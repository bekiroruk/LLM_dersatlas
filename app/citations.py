import re


def valid_citations(answer, selected, known):
    """Kaynak kimliklerini kontrol eder; iddiaların anlamsal doğruluğunu kanıtlamaz."""
    cited = set(re.findall(r"\[(K\d+)\]", answer))
    selected = set(selected)
    return bool(answer.strip() and cited and cited == selected and selected.issubset(set(known)))
