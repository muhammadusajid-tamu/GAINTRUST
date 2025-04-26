from dataclasses import dataclass


@dataclass(frozen=True)
class Options:
    benchmark_name: str
    submodule_name: str
    tag: str
    n_prompt_examples: int = 4
    timeout: int = 3
    restart_budget: int = 3
    fix_budget: int = 5
    fallback_opt: str = "fix"  # choices = ["restart", "param-search", "prompt-search", "simplify", "fix"]"
    language: str = "c"  # choices = ["c", "go"]
    comp_fix: str = "base"  # choices = ["base", "adv", "beam", "msft"]
    comp_fix_attempt_budget: int = 3
    sem_fix: str = "base"  # choices=["base", "llm-fl", "pa-fl", "llm-explain"]
    initial_temperature: float = 0.2
    hinted: bool = False
    conversation: bool = False
    conversation_window_size: int = 3
    pruning: bool = False
    beam_width: int = 1
    n_fix_peers: int = 1
    transpl_attempt_budget: int = 3
    model: str = "local-qwen"

    @property
    def work_dir(self) -> str:
        return (
            f"transpilations/{self.model}/{self.language}/{self.benchmark_name}/{self.tag}/"
        )

    @property
    def res_dir(self) -> str:
        return f"{self.work_dir}/results"

    @property
    def comp_fix_m(self) -> str:
        return "comp-" + self.comp_fix + "-fix"

    @property
    def sem_fix_m(self) -> str:
        return "sem-" + self.sem_fix + "-fix"

    @property
    def fix_settings_path(self) -> str:
        if self.fallback_opt == "fix":
            conversation_setting: str
            if not self.conversation:
                conversation_setting = "False"
            else:
                conversation_setting = "True"
            ce_setting = ""
            if self.n_prompt_examples == 0:
                assert not self.conversation, "CAPR requires counter examples"
                ce_setting = "wo-ce/"
            return f"{self.sem_fix_m}/fix-{self.fix_budget}/beam-width-{self.beam_width}/n-fix-peers-{self.n_fix_peers}/{ce_setting}conversational-{conversation_setting}/pruning-{self.pruning}/"
        else:
            return "/"

    @property
    def restart_settings_path(self) -> str:
        return f"restart-{self.restart_budget}/hinted-{self.hinted}/"
