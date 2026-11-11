import re
import time
import unicodedata
from typing import List, Tuple, Optional, Set
from collections import OrderedDict


def normalize_text(text: str) -> str:
    """
    Remove acentos, normaliza espaços e converte para minúsculas.
    Exemplo: 'Promoção: Teclado Mecânico!' -> 'promocao: teclado mecanico!'
    """
    if not text:
        return ""
    # Decompõe caracteres acentuados (ex: 'ç' -> 'c' + '~')
    normalized = unicodedata.normalize('NFKD', text)
    # Remove marcas diacríticas (acentos)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    return stripped.lower().strip()


def parse_keyword_rule(raw_kw: str) -> Tuple[str, Optional[float]]:
    """
    Interpreta termos simples ou com teto de preço:
    - 'rtx 4060' -> ('rtx 4060', None)
    - 'rtx 4060 < 2000' -> ('rtx 4060', 2000.0)
    - 'ps5 <= 3.500,00' -> ('ps5', 3500.0)
    """
    match = re.match(r'^(.*?)\s*(?:<=|<)\s*([0-9\.,]+)$', raw_kw.strip(), re.IGNORECASE)
    if match:
        term = match.group(1).strip()
        price_str = match.group(2).replace('.', '').replace(',', '.')
        try:
            return term, float(price_str)
        except ValueError:
            return raw_kw.strip(), None
    return raw_kw.strip(), None


def extract_prices(text: str) -> List[float]:
    """Extrai valores em Reais (R$) encontrados no texto."""
    if not text:
        return []
    # Captura padrões como R$ 1.999,90, R$150,00, R$ 250, etc.
    pattern = r'R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{1,2})?|[0-9]+(?:,[0-9]{1,2})?)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    prices = []
    for m in matches:
        clean = m.replace('.', '').replace(',', '.')
        try:
            val = float(clean)
            if val > 0:
                prices.append(val)
        except ValueError:
            pass
    return prices


class FilterEngine:
    def __init__(self, keywords: List[str], negative_keywords: List[str], cooldown_minutes: int = 15):
        self.cooldown_seconds = cooldown_minutes * 60
        self.history: OrderedDict[str, float] = OrderedDict()  # hash -> timestamp
        self.update_rules(keywords, negative_keywords, cooldown_minutes)

    def update_rules(self, keywords: List[str], negative_keywords: List[str], cooldown_minutes: Optional[int] = None):
        """Atualiza a lista de termos e recompila as expressões regulares."""
        if cooldown_minutes is not None:
            self.cooldown_seconds = cooldown_minutes * 60

        self.raw_keywords = [k.strip() for k in keywords if k.strip()]
        self.raw_negative = [k.strip() for k in negative_keywords if k.strip()]

        # Compila padrões positivos
        self.positive_patterns = []
        for kw in self.raw_keywords:
            clean_term, max_price = parse_keyword_rule(kw)
            norm_kw = normalize_text(clean_term)
            if not norm_kw:
                continue
            # Fronteira de palavra alfanumérica
            pattern = re.compile(rf'(?<![a-zA-Z0-9_]){re.escape(norm_kw)}(?![a-zA-Z0-9_])', re.IGNORECASE)
            self.positive_patterns.append((kw, clean_term, max_price, pattern))

        # Compila padrões negativos (palavras a ignorar)
        self.negative_patterns = []
        for neg in self.raw_negative:
            norm_neg = normalize_text(neg)
            if not norm_neg:
                continue
            pattern = re.compile(rf'(?<![a-zA-Z0-9_]){re.escape(norm_neg)}(?![a-zA-Z0-9_])', re.IGNORECASE)
            self.negative_patterns.append((neg, pattern))

    def _cleanup_history(self, current_time: float):
        """Remove registros antigos do histórico de duplicatas."""
        if self.cooldown_seconds <= 0:
            self.history.clear()
            return
        cutoff = current_time - self.cooldown_seconds
        to_remove = []
        for h, t in self.history.items():
            if t < cutoff:
                to_remove.append(h)
            else:
                break
        for h in to_remove:
            del self.history[h]

    def _generate_fingerprint(self, text: str, urls: Optional[List[str]] = None) -> str:
        """Gera uma assinatura única da mensagem (baseada em URLs ou trecho do texto)."""
        if urls and len(urls) > 0:
            # Se a mensagem contiver links, o primeiro link principal é a melhor assinatura
            return f"url:{urls[0].lower().strip()}"
        # Caso contrário, usa os primeiros 100 caracteres normalizados sem espaços
        norm = normalize_text(text)
        condensed = re.sub(r'\s+', '', norm)[:100]
        return f"text:{condensed}"

    def check_message(self, text: str, urls: Optional[List[str]] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Avalia o texto da mensagem.
        Retorna:
          (aprovado: bool, termo_positivo_correspondente: str ou None, motivo_bloqueio: str ou None)
        """
        if not text:
            return False, None, "Mensagem sem texto"

        norm_text = normalize_text(text)
        now = time.time()
        self._cleanup_history(now)

        # 1. Verifica se contém alguma palavra negativa (blacklist)
        for raw_neg, pat in self.negative_patterns:
            if pat.search(norm_text):
                return False, None, f"Contém palavra bloqueada: '{raw_neg}'"

        # 2. Verifica se contém alguma palavra positiva (whitelist)
        matched_term = None
        price_blocked_reason = None
        extracted = None

        for raw_kw, clean_term, max_price, pat in self.positive_patterns:
            if pat.search(norm_text):
                # Se tem teto de preço definido, valida com os preços da mensagem
                if max_price is not None:
                    if extracted is None:
                        extracted = extract_prices(text)
                    if extracted:
                        lowest_price = min(extracted)
                        if lowest_price > max_price:
                            price_blocked_reason = f"Preço de R$ {lowest_price:.2f} acima do teto de R$ {max_price:.2f} para '{clean_term}'"
                            continue
                matched_term = raw_kw
                break

        if not matched_term:
            return False, None, price_blocked_reason or "Nenhum termo de interesse encontrado"

        # 3. Verifica duplicatas recentes (se cooldown > 0)
        if self.cooldown_seconds > 0:
            fingerprint = self._generate_fingerprint(text, urls)
            if fingerprint in self.history:
                return False, None, f"Promoção repetida (ignorada pelo cooldown de {int(self.cooldown_seconds / 60)} min)"

            # Registra no histórico
            self.history[fingerprint] = now

        return True, matched_term, None

