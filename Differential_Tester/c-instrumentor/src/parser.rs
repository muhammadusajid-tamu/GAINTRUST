//! A Parser for C data

use nom::{
    branch::alt,
    bytes::complete::{is_not, tag, take_until},
    // see the "streaming/complete" paragraph lower for an explanation of these submodules
    character::complete::{alpha1, alphanumeric1, char, crlf, newline, tab},
    combinator::{all_consuming, map, opt, recognize, value},
    error::ParseError,
    multi::{many0, many0_count, many1, many1_count, separated_list0, separated_list1},
    sequence::{delimited, pair, preceded, terminated, tuple},
    IResult,
};

use crate::{CFnSig, CStruct};

fn identifier(input: &str) -> IResult<&str, &str> {
    recognize(pair(
        alt((alpha1, tag("_"))),
        many0_count(alt((alphanumeric1, tag("_")))),
    ))(input)
}

fn array_declarator(input: &str) -> IResult<&str, Vec<String>> {
    many0(delimited(
        token(char('[')),
        map(recognize(opt(is_not("]"))), |expr: &str| expr.to_owned()),
        token(char(']')),
    ))(input)
}

fn designator(input: &str) -> IResult<&str, &str> {
    alt((tag("const"), tag("static"), tag("inline")))(input)
}

fn modifier(input: &str) -> IResult<&str, &str> {
    alt((tag("signed"), tag("unsigned"), tag("long"), tag("short")))(input)
}

fn arithmetic_type(input: &str) -> IResult<&str, &str> {
    alt((
        tag("int8_t"),
        tag("int16_t"),
        tag("int32_t"),
        tag("int64_t"),
        tag("char"),
        tag("int"),
        tag("float"),
        tag("double"),
    ))(input)
}

fn primitive_type(input: &str) -> IResult<&str, String> {
    alt((
        map(
            alt((
                pair(many1(token(modifier)), opt(token(arithmetic_type))),
                pair(many0(token(modifier)), map(token(arithmetic_type), Some)),
            )),
            |(modifiers, opt_type)| {
                modifiers
                    .iter()
                    .copied()
                    .chain(opt_type)
                    .map(|s| s.to_owned())
                    .collect::<Vec<_>>()
                    .join(" ")
            },
        ),
        map(token(tag("bool")), |s: &str| s.to_owned()),
    ))(input)
}

fn type_alias_or_complex(input: &str) -> IResult<&str, String> {
    alt((
        map(
            preceded(terminated(tag("struct"), dont_care1), identifier),
            |s| format!("struct {s}"),
        ),
        map(
            preceded(terminated(tag("enum"), dont_care1), identifier),
            |s| format!("enum {s}"),
        ),
        map(identifier, |s| s.to_owned()),
    ))(input)
}

fn type_name(input: &str) -> IResult<&str, String> {
    map(
        tuple((
            opt(token(designator)),
            alt((token(primitive_type), token(type_alias_or_complex))),
            opt(token(tag("const"))),
            many0(token(char('*'))),
        )),
        |(_, mut ty, _, opt_star)| {
            // opt_star.map(|_| ty.push('*'));
            opt_star.into_iter().for_each(|_| ty.push('*'));
            ty
        },
    )(input)
}

/// Procuce field_name: type_name
fn field_def(input: &str) -> IResult<&str, (String, Vec<(String, Vec<String>)>)> {
    terminated(
        tuple((
            token(type_name),
            separated_list1(token(char(',')), pair(map(token(identifier), |ident| ident.to_owned()), array_declarator))
        )),
        token(char(';')),
    )(input)
}

fn peol_comment<'a, E: ParseError<&'a str>>(input: &'a str) -> IResult<&'a str, (), E> {
    value(
        (), // Output is thrown away.
        pair(tag("//"), is_not("\n\r")),
    )(input)
}

fn pinline_comment<'a, E: ParseError<&'a str>>(input: &'a str) -> IResult<&'a str, (), E> {
    value(
        (), // Output is thrown away.
        tuple((tag("/*"), take_until("*/"), tag("*/"))),
    )(input)
}

fn dont_care0<'a, E: ParseError<&'a str>>(input: &'a str) -> IResult<&'a str, (), E> {
    value(
        (),
        many0_count(alt((
            value((), alt((char(' '), newline, tab))),
            value((), crlf),
            peol_comment,
            pinline_comment,
        ))),
    )(input)
}

fn dont_care1<'a, E: ParseError<&'a str>>(input: &'a str) -> IResult<&'a str, (), E> {
    value(
        (),
        many1_count(alt((
            value((), alt((char(' '), newline, tab))),
            value((), crlf),
            peol_comment,
            pinline_comment,
        ))),
    )(input)
}

fn token<'a, F: 'a, O, E: ParseError<&'a str>>(
    inner: F,
) -> impl FnMut(&'a str) -> IResult<&'a str, O, E>
where
    F: FnMut(&'a str) -> IResult<&'a str, O, E>,
{
    delimited(dont_care0, inner, dont_care0)
}

fn struct_typedef_impl(input: &str) -> IResult<&str, CStruct> {
    map(
        delimited(
            tuple((token(tag("typedef")), token(tag("struct")))),
            tuple((
                opt(token(identifier)),
                delimited(token(char('{')), many0(field_def), token(char('}'))),
                token(identifier),
            )),
            token(char(';')),
        ),
        |(_, fields, ident)| {
            let fields = fields.into_iter().flat_map(move |(ty, fields)| {
                fields.into_iter().map(move |(name, array_decls)| {
                    (name, ty.clone(), array_decls)
                })
            }).collect::<Vec<_>>();
            CStruct {
                ident: ident.to_owned(),
                fields
            }
        },
    )(input)
}

fn struct_decl_impl(input: &str) -> IResult<&str, CStruct> {
    println!("struct_decl: attempting {input}");
    map(
        delimited(
            token(tag("struct")),
            pair(
                token(identifier),
                delimited(token(char('{')), many0(field_def), token(char('}'))),
            ),
            token(char(';')),
        ),
        |(ident, fields)| {
            let fields = fields.into_iter().flat_map(move |(ty, fields)| {
                fields.into_iter().map(move |(name, array_decls)| {
                    (name, ty.clone(), array_decls)
                })
            }).collect::<Vec<_>>();
            CStruct {
                ident: ident.to_owned(),
                fields
            }
        },
    )(input)
}

pub fn struct_def(input: &str) -> IResult<&str, CStruct> {
    (all_consuming(alt((struct_typedef_impl, struct_decl_impl))))(input)
}

fn fn_decl_impl(input: &str) -> IResult<&str, CFnSig> {
    map(
        terminated(
            tuple((
                token(type_name),
                token(identifier),
                delimited(
                    token(char('(')),
                    separated_list0(
                        token(char(',')),
                        pair(
                            token(type_name),
                            preceded(opt(token(identifier)), array_declarator),
                        ),
                    ),
                    token(char(')')),
                ),
            )),
            token(char(';')),
        ),
        |(ret, ident, args)| CFnSig {
            ident: ident.to_owned(),
            args,
            ret,
        },
    )(input)
}

pub fn fn_sig(input: &str) -> IResult<&str, CFnSig> {
    (all_consuming(fn_decl_impl))(input)
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test() {
        assert!(type_name("static unsigned long long int")
            .is_ok_and(|(remaining, _)| remaining.is_empty()));

        assert!(type_name("float").is_ok_and(|(remaining, _)| remaining.is_empty()));

        assert!(field_def("  int  *  qeofuef_teftbGEGTE_    ;")
            .is_ok_and(|(remaining, _)| remaining.is_empty()));

        assert!(field_def("  wchar_t    qeofuef_teftbGEGTE_    ;")
            .is_ok_and(|(remaining, _)| remaining.is_empty()));
        assert!(
            struct_def("typedef struct url_parse { int f; } url_parse_t ;")
                .is_ok_and(|(remaining, _)| remaining.is_empty())
        );
        assert!(
            struct_def("typedef struct { int f;    char*   g  ;  int    *h; } url_parse_t ;")
                .is_ok_and(|(remaining, _)| { remaining.is_empty() })
        );
        assert!(
            struct_def("struct url_parse_t { int f;    char*   g  ;  int    *h; }  ;")
                .is_ok_and(|(remaining, _)| { remaining.is_empty() })
        );
        assert!(fn_sig("char  * foobar  (int x,   char  *   , bool );")
            .is_ok_and(|(remaining, _)| remaining.is_empty()));

        assert!(fn_sig("char*   foobar  (int x,   char  *   , bool );")
            .is_ok_and(|(remaining, _)| remaining.is_empty()));

        assert!(fn_sig(
            "void add_child16(art_node16 *n, art_node **ref, unsigned char c, void *child) ;"
        )
        .is_ok());

        assert!(struct_def(
            "struct json_parse_state_s {
                const char *src;
                size_t size;
                size_t offset;
                size_t flags_bitset;
                char *data;
                char *dom;
                size_t dom_size;
                size_t data_size;
                size_t line_no;     /* line counter for error reporting. */
                size_t line_offset; /* (offset-line_offset) is the character number (in
                                       bytes). */
                size_t error;
              };"
        )
        .is_ok());

        assert!(field_def("unsigned char modulator_40, carrier_40;").is_ok());

        assert!(struct_typedef_impl(
            "typedef struct opl_timbre_t {
                unsigned long modulator_E862, carrier_E862;
                unsigned char modulator_40, carrier_40;
                unsigned char feedconn;
                signed char finetune;
                unsigned char notenum;
                signed short noteoffset;
              } opl_timbre_t;"
        ).is_ok());

        assert!(fn_sig("int json_skip_whitespace(struct json_parse_state_s *state) ;").is_ok());
    }
}
