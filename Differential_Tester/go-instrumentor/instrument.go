package main

import (
	"bufio"
	"bytes"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"log"
	"os"
	"strings"
	"unicode"
)

func main() {
	fileName := os.Args[1]
	fset := token.NewFileSet() // positions are relative to fset
	// Parse the file given in arguments
	f, err := parser.ParseFile(fset, fileName, nil, parser.ParseComments)
	if err != nil {
		fmt.Printf("Error parsing file %v", err)
		return
	}

	// delete this import and add a new one
	DeleteImport(fset, f, "C")
	AddImport(fset, f, "encoding/json")
	AddImport(fset, f, "unsafe")
	AddImport(fset, f, "bytes")
	AddImport(fset, f, "runtime")

	AddImport(fset, f, "strings")
	AddImport(fset, f, "fmt")
	ReplaceByteArray(f)
	RemoveMultiDecls(f)
	GenerateTags(f)
	wrappers := GenerateWrapper(f)
	var wrapperStr string
	for _, wrapper := range wrappers {
		wrapperStr += wrapper
	}

	// overwrite the file with modified version of ast.
	write, err := os.Create(fileName)
	if err != nil {
		fmt.Printf("Error opening file %v", err)
		return
	}
	defer write.Close()
	w := bufio.NewWriter(write)
	err = format.Node(w, fset, f)
	if err != nil {
		fmt.Printf("Error formating file %s", err)
		return
	}

	w.Write([]byte(wrapperStr))
	w.Flush()

	// LOL
	file, err := os.ReadFile(fileName)
	if err != nil {
		fmt.Printf("Error parsing file %v", err)
		return
	}

	var output string
	lines := strings.Split(string(file), "\n")

	packageRenamed := false
	for _, line := range lines {
		if strings.Index(line, "package") == 0 {
			if !strings.Contains(line, "main") {
				line = "package main"
				packageRenamed = true
			}
			output += line + "\n"
			output += `// #include <stdlib.h>
// #include <string.h>
import "C"`
			output += "\n"
		} else {
			output += line + "\n"
		}
	}
	if packageRenamed {
		output += "func main() {}\n"
	}
	output += `
func abort_if_panic() {
	if r := recover(); r != nil {
		runtime.GC()
		C.abort()
	}
}
`
	output += `
type JSONableSlice []uint8

func (u JSONableSlice) MarshalJSON() ([]byte, error) {
	var result string
	if u == nil {
		result = "null"
	} else {
		result = strings.Join(strings.Fields(fmt.Sprintf("%d", u)), ",")
	}
	return []byte(result), nil
}
`
	output += "var _ = unsafe.StringData(\"\")\n"
	output += `
	// Marshal is a UTF-8 friendly marshaler.  Go's json.Marshal is not UTF-8
	// friendly because it replaces the valid UTF-8 and JSON characters "&". "<",
	// ">" with the "slash u" unicode escaped forms (e.g. \u0026).  It preemptively
	// escapes for HTML friendliness.  Where text may include any of these
	// characters, json.Marshal should not be used. Playground of Go breaking a
	// title: https://play.golang.org/p/o2hiX0c62oN
	func Marshal(i interface{}) ([]byte, error) {
		buffer := &bytes.Buffer{}
		encoder := json.NewEncoder(buffer)
		encoder.SetEscapeHTML(false)
		err := encoder.Encode(i)
		return bytes.TrimRight(buffer.Bytes(), "\n"), err
	}`

	err = os.WriteFile(fileName, []byte(output), 0644)
	if err != nil {
		panic(err)
	}
}

func GenerateWrapper(f ast.Node) []string {

	var fns []goFuncType

	ast.Inspect(f, func(n ast.Node) bool {
		switch t := n.(type) {
		case *ast.FuncDecl:
			if t.Name.Name != "main" {
				processFunc(t, &fns)
			}
			return false
		}
		return true
	})

	var wrappers []string

	for _, fn := range fns {
		// fmt.Printf("%s\n", fn.ToString())
		wrapper := funcWrapperString(&fn)
		// fmt.Printf("%s\n", wrapper)
		wrappers = append(wrappers, wrapper)
	}

	return wrappers
}

func processFunc(x *ast.FuncDecl, fns *[]goFuncType) {
	fn, ok := funcSiganture(x)
	if ok {
		*fns = append(*fns, fn)
	}
}

type typeKind int

const (
	complexType   = 0
	primitiveType = 1
)

type goType struct {
	path string
	kind typeKind
}

func (ty *goType) ToString() string {
	return ty.path
}

type goFuncType struct {
	name     string
	receiver *goType
	input    []goType
	output   []goType
}

func (ty *goFuncType) ToString() string {
	var ret string
	if ty.receiver != nil {
		ret = fmt.Sprintf("(%s) %s", ty.receiver.ToString(), ty.name)
	} else {
		ret = ty.name
	}
	ret += "("
	for _, ty := range ty.input {
		ret += ty.ToString() + ","
	}
	ret += ")"

	ret += "("
	for _, ty := range ty.output {
		ret += ty.ToString() + ","
	}
	ret += ")"
	return ret
}

func funcSiganture(x *ast.FuncDecl) (ret goFuncType, ok bool) {
	var input []goType
	var output []goType
	ok = true
	if x.Recv != nil {
		if x.Recv.NumFields() != 1 {
			panic("wat")
		}
		recv := x.Recv.List[0]
		ty, gold := resolveTypeExpr(recv.Type)
		if !gold {
			ok = false
			return
		}
		ret.receiver = &ty
	}

	for _, field := range x.Type.Params.List {
		ty, gold := resolveTypeExpr(field.Type)
		if !gold {
			ok = false
			return
		}
		for _, _ = range field.Names {
			input = append(input, ty)
		}
	}
	if x.Type.Results != nil {
		for _, field := range x.Type.Results.List {
			ty, gold := resolveTypeExpr(field.Type)
			if !gold {
				ok = false
				return
			}
			output = append(output, ty)
		}
	}
	ret.name = x.Name.Name
	ret.input = input
	ret.output = output
	return
}

func funcWrapperString(ty *goFuncType) (ret string) {
	if ty.receiver != nil {
		runes := []rune(ty.name)
		runes[0] = unicode.ToUpper(runes[0])
		name := strings.TrimPrefix(ty.receiver.ToString(), "*") + string(runes)
		ret += fmt.Sprintf("//export %s__C\n", ToSnake(name))
	} else {
		ret += fmt.Sprintf("//export %s__C\n", ToSnake(ty.name))
	}
	// parameter string
	var paramsStr string
	if ty.receiver != nil {
		var tyStr string
		if ty.receiver.kind == primitiveType {
			tyStr = ty.receiver.ToString()
		} else {
			tyStr = "*C.char"
		}
		paramsStr += fmt.Sprintf("extern_receiver %s, ", tyStr)
	}
	for index, ty := range ty.input {
		var tyStr string
		if ty.kind == primitiveType {
			tyStr = ty.ToString()
		} else {
			tyStr = "*C.char"
		}
		paramsStr += fmt.Sprintf("extern_input%d %s, ", index, tyStr)
	}

	errorHandling := false
	if len(ty.output) >= 1 && ty.output[len(ty.output)-1].path == "error" {
		errorHandling = true
		// remove the error output parameter
		ty.output = ty.output[:len(ty.output)-1]
	}
	// output string
	const (
		noOutput          = 0
		outputIsPrimitive = 1
		outputIsComplex   = 2
	)
	outputKind := noOutput
	if len(ty.output) == 1 && ty.output[0].kind == primitiveType {
		outputKind = outputIsPrimitive
	} else if len(ty.output) > 0 {
		outputKind = outputIsComplex
	}
	var outputStr string
	switch outputKind {
	case noOutput:
	case outputIsPrimitive:
		outputStr = ty.output[0].ToString()
	case outputIsComplex:
		outputStr = "*C.char"
	}

	// signature line
	if ty.receiver != nil {
		runes := []rune(ty.name)
		runes[0] = unicode.ToUpper(runes[0])
		name := strings.TrimPrefix(ty.receiver.ToString(), "*") + string(runes)
		ret += fmt.Sprintf("func %s__C(%s) %s {\n", ToSnake(name), paramsStr, outputStr)
	} else {
		ret += fmt.Sprintf("func %s__C(%s) %s {\n", ToSnake(ty.name), paramsStr, outputStr)
	}

	ret += "defer abort_if_panic()\n"

	// predefine err
	ret += "var err error\nif err == nil {}\n"

	// prepare arguments
	if ty.receiver != nil {
		if ty.receiver.kind == primitiveType {
			ret += fmt.Sprintf("receiver := extern_receiver\n")
		} else {
			tyStr := ty.receiver.ToString()
			ret += fmt.Sprintf("var receiver %s\n", tyStr)
			ret += fmt.Sprintf("err = json.Unmarshal([]byte(C.GoString(extern_receiver)), &receiver)\n")
			ret += fmt.Sprintf("if err != nil { panic(err) }\n")
		}
	}
	for index, ty := range ty.input {
		if ty.kind == primitiveType {
			ret += fmt.Sprintf("input%d := extern_input%d\n", index, index)
		} else {
			tyStr := ty.ToString()
			ret += fmt.Sprintf("var input%d %s\n", index, tyStr)
			ret += fmt.Sprintf("err = json.Unmarshal([]byte(C.GoString(extern_input%d)), &input%d)\n", index, index)
			ret += fmt.Sprintf("if err != nil { panic(err) }\n")
		}
	}

	// assemble arguments
	var argsStr string
	for index, _ := range ty.input {
		argsStr += fmt.Sprintf("input%d, ", index)
	}

	// call
	var callStr string
	if ty.receiver != nil {
		callStr = fmt.Sprintf("receiver.%s(%s)\n", ty.name, argsStr)
	} else {
		callStr = fmt.Sprintf("%s(%s)\n", ty.name, argsStr)
	}
	switch outputKind {
	case noOutput:
		if errorHandling {
			ret += fmt.Sprintf("err = %s\n", callStr)
			ret += fmt.Sprintf("if err != nil { panic(\"execution failure\") }\n")
		} else {
			ret += callStr
		}
	default:
		outputs := []string{}
		for idx, _ := range ty.output {
			outputs = append(outputs, fmt.Sprintf("output%d", idx))
		}
		outputTuple := strings.Join(outputs, ", ")
		if errorHandling {
			ret += fmt.Sprintf("%s, err := %s\n", outputTuple, callStr)
			ret += fmt.Sprintf("if err != nil { panic(\"execution failure\") }\n")
		} else {
			ret += fmt.Sprintf("%s := %s\n", outputTuple, callStr)
		}
		if len(ty.output) > 1 {
			ret += fmt.Sprintf("output := []interface{}{%s}\n", outputTuple)
		} else {
			ret += fmt.Sprintf("output := %s\n", outputTuple)
		}
	}

	// set input
	if ty.receiver != nil {
		if ty.receiver.kind == complexType {
			ret += fmt.Sprintf("serialized_receiver, err := Marshal(receiver)\n")
			ret += fmt.Sprintf("if err != nil { panic(err) }\n")
			ret += fmt.Sprintf("new_extern_receiver := C.CString(string(serialized_receiver))\n")
			ret += fmt.Sprintf("C.strcpy(extern_receiver, new_extern_receiver)\n")
			ret += fmt.Sprintf("C.free(unsafe.Pointer(new_extern_receiver))\n")
		}
	}
	for index, ty := range ty.input {
		if ty.kind == complexType {
			ret += fmt.Sprintf("serialized_input%d, err := Marshal(input%d)\n", index, index)
			ret += fmt.Sprintf("if err != nil { panic(err) }\n")
			ret += fmt.Sprintf("new_extern_input%d := C.CString(string(serialized_input%d))\n", index, index)
			ret += fmt.Sprintf("C.strcpy(extern_input%d, new_extern_input%d)\n", index, index)
			ret += fmt.Sprintf("C.free(unsafe.Pointer(new_extern_input%d))\n", index)
		}
	}

	// return
	switch outputKind {
	case noOutput:
	case outputIsPrimitive:
		ret += "return output\n"
	case outputIsComplex:
		// outputTy := ty.output[0].ToString()
		ret += fmt.Sprintf("var externOutput []byte\n")
		ret += fmt.Sprintf("externOutput, err = Marshal(output)\n")
		ret += fmt.Sprintf("if err != nil { panic(err) }\n")
		ret += "return C.CString(string(externOutput))\n"
	}

	ret += "}\n"
	return
}

// Return the string representation fo this expression. `gold == false` if
// out of scope
func resolveTypeExpr(e ast.Expr) (ty goType, gold bool) {
	gold = false
	ty.path = ExprToString(e)
	ty.kind = complexType
	switch t := e.(type) {
	case *ast.Ident:
		gold = true
		switch t.Name {
		case "float32":
			fallthrough
		case "float64":
			fallthrough
		case "byte":
			fallthrough
		case "uint8":
			fallthrough
		case "uint":
			fallthrough
		case "uint32":
			fallthrough
		case "uint64":
			fallthrough
		case "int8":
			fallthrough
		case "int":
			fallthrough
		case "int32":
			fallthrough
		case "int64":
			fallthrough
		case "bool":
			ty.kind = primitiveType
		}
	case *ast.StarExpr:
		// _, gold = t.X.(*ast.Ident)
		gold = true
	case *ast.ArrayType:
		_, gold = t.Elt.(*ast.Ident)
	case *ast.StructType:
		// explicit struct types are not handled
	case *ast.FuncType:
		// func types are not handled
	case *ast.InterfaceType:
		// interface types are not handled
	case *ast.MapType:
		_, gold = t.Key.(*ast.Ident)
		_, ok := t.Value.(*ast.Ident)
		gold = gold && ok
	}
	return
}

func ReplaceByteArray(f ast.Node) {
	ast.Inspect(f, func(n ast.Node) bool {
		switch t := n.(type) {
		case *ast.StructType:
			replaceByteArray(t)
			return false
		}
		return true
	})
}

func replaceByteArray(x *ast.StructType) {
	for _, field := range x.Fields.List {
		if len(field.Names) == 0 {
			continue
		}

		if ExprToString(field.Type) == "[]byte" {
			field.Type = &ast.Ident{Name: "JSONableSlice"}
		}
	}
}

func RemoveMultiDecls(f ast.Node) {
	ast.Inspect(f, func(n ast.Node) bool {
		switch t := n.(type) {
		case *ast.StructType:
			processMultiDecls(t)
			return false
		}
		return true
	})
}

func processMultiDecls(x *ast.StructType) {
	newFieldsList := make([]*ast.Field, 0, 2)
	for _, field := range x.Fields.List {

		if len(field.Names) == 0 {
			newFieldsList = append(newFieldsList, field)
		} else {
			for _, name := range field.Names {
				newField := ast.Field{}
				// newName := ast.NewIdent(strings.Title(name.Name))
				newName := *name
				newField.Names = []*ast.Ident{&newName}
				newField.Type = field.Type
				newFieldsList = append(newFieldsList, &newField)
			}
		}
	}
	x.Fields.List = newFieldsList
}

// GenerateTags generates snake case json tags so that you won't need to write them. Can be also extended to xml or sql tags
func GenerateTags(f ast.Node) {
	// range over the objects in the scope of this generated AST and check for StructType. Then range over fields
	// contained in that struct.

	ast.Inspect(f, func(n ast.Node) bool {
		switch t := n.(type) {
		case *ast.StructType:
			processTags(t)
			return false
		}
		return true
	})
}

func processTags(x *ast.StructType) {
	for _, field := range x.Fields.List {
		if len(field.Names) == 0 {
			continue
		}

		if field.Tag == nil {
			field.Tag = &ast.BasicLit{}
			field.Tag.ValuePos = field.Type.Pos() + 1
			field.Tag.Kind = token.STRING
		}

		fieldName := field.Names[0].String()

		newTags := fmt.Sprintf("`json:\"%s\"`", ToSnake(fieldName))
		field.Tag.Value = newTags
	}
}

// ToSnake convert the given string to snake case following the Golang format:
// acronyms are converted to lower-case and preceded by an underscore.
// Original source : https://gist.github.com/elwinar/14e1e897fdbe4d3432e1
func ToSnake(in string) string {
	runes := []rune(in)
	length := len(runes)

	var out []rune
	for i := 0; i < length; i++ {
		if i > 0 && unicode.IsUpper(runes[i]) && ((i+1 < length && unicode.IsLower(runes[i+1])) || unicode.IsLower(runes[i-1])) {
			out = append(out, '_')
		}
		out = append(out, unicode.ToLower(runes[i]))
	}
	return string(out)
}

func ExprToString(node ast.Expr) string {
	fset := token.NewFileSet()

	var buf bytes.Buffer
	err := format.Node(&buf, fset, node)
	if err != nil {
		log.Fatal(err)
	}
	return buf.String()
}
