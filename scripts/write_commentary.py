"""Build data/annotated/phrase_commentary.json from the current top-20 tables.

Phrase facts were written after reading those tables. Score and frequency
placeholders are filled later by the pipeline from the same rows.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GOLD = set(pd.read_csv(ROOT / "data/annotated/gold_collocations.csv")["phrase"])

# Specific description of the phrase in this corpus. Label is genuine only
# when the phrase is on the gold list; the generator checks that.
FACTS: dict[str, tuple[str, str]] = {
    "aaron scott": ("genuine", "Fixed personal name (given name plus surname) from the meeting floor."),
    "and i": ("junk", "Coordinator plus first-person pronoun. It is syntax, not a term."),
    "and i be": ("junk", "Lemmatized 'and I am'. The copula was collapsed to 'be', so the trigram is an artifact."),
    "and i think": ("junk", "A discourse opener, freely composed, not a taggable term."),
    "annual action plan": ("acceptable", "A real planning document name (annual action plan) that was not put on the gold list."),
    "as well": ("acceptable", "A fixed additive discourse formula, deliberately not a domain tag."),
    "attorney fee": ("genuine", "Fixed legal-finance compound, lemmatized from 'attorney fees'."),
    "be able to": ("junk", "Lemmatized 'be able to', an ordinary verb chain."),
    "be go to": ("junk", "Lemmatized 'is going to' or 'are going to'. The tagger turned the progressive into 'go'."),
    "boot camp": ("genuine", "Fixed program name. The two words do not productively swap."),
    "brook tucker": ("genuine", "Fixed personal name."),
    "cabo verde": ("genuine", "Country name used as a hearing topic, not a compositional pairing."),
    "cape verdean": ("acceptable", "Demonym for the Cabo Verde community. Real, and not on the gold list, which kept the place name instead."),
    "capitol hill": ("genuine", "Fixed neighborhood name."),
    "cfd dash two": ("junk", "An agenda code tokenized into three pieces ('CFD', the word 'dash', and 'two'). Not a phrase."),
    "civil right utility": ("junk", "A slice of the committee title 'Civil Rights, Utilities, Economic Development' after the comma disappeared and 'rights' was lemmatized."),
    "coffee shop": ("genuine", "Fixed commercial compound."),
    "core mission": ("acceptable", "Fixed institutional noun ('core mission') left off the gold list."),
    "council member": ("genuine", "The standard role title in this corpus."),
    "do not": ("junk", "Clitic repair of 'don't' plus the auxiliary. Grammatical, not topical."),
    "domestic violence": ("genuine", "Fixed policy term."),
    "dry ice": ("genuine", "Fixed substance name that happens to be the topic of one hearing."),
    "estate master plan": ("acceptable", "The tail of 'real estate master plan'. The full name is longer than this trigram window."),
    "favor please signify": ("acceptable", "A slice of the voting formula 'in favor please signify'. Procedural, and not the trigram that was gold-listed."),
    "go to": ("junk", "A high-frequency verb plus particle."),
    "go to be": ("junk", "Lemmatized 'going to be'."),
    "housing task force": ("genuine", "Fixed body name."),
    "human relation board": ("genuine", "Fixed board name, with 'relations' lemmatized to 'relation'."),
    "i be": ("junk", "Lemmatized 'I am'. A copula artifact, not a collocation."),
    "i do not": ("junk", "Lemmatized negation, ordinary syntax."),
    "i just want": ("junk", "A discourse preface before a request."),
    "i thank you": ("acceptable", "A politeness variant of 'thank you', not a domain tag."),
    "i think": ("junk", "A stance marker. Speakers use it with any complement."),
    "i think that": ("junk", "Stance marker plus complementizer."),
    "i want to": ("junk", "The most common request preface in the transcripts."),
    "i would": ("junk", "Pronoun plus modal. No lexical cohesion."),
    "i would like": ("junk", "A politeness preface, compositionally built."),
    "in the": ("junk", "Preposition plus determiner, the prototype of grammatical co-occurrence."),
    "it be": ("junk", "Lemmatized 'it is'."),
    "just want to": ("junk", "Request preface with 'just'."),
    "kind of": ("acceptable", "A fixed hedge. Not a domain tag, and not random."),
    "law enforcement oversight": ("genuine", "Fixed oversight-policy trigram."),
    "lombardi trophy": ("genuine", "Fixed trophy name."),
    "long beach": ("genuine", "City name, non-compositional."),
    "look at": ("junk", "Verb plus particle, freely composed."),
    "low scale residential": ("genuine", "Fixed zoning description."),
    "maiden speech": ("genuine", "Fixed parliamentary formula for a member's first speech."),
    "make sure": ("acceptable", "A fixed discourse verb. Not a topic tag."),
    "make sure that": ("acceptable", "The same discourse verb with a complementizer. Not gold."),
    "maximum building height": ("genuine", "Fixed zoning measure."),
    "mile high stadium": ("genuine", "Fixed stadium name."),
    "mm hmm": ("junk", "A backchannel. The two syllables almost never occur apart, so dependence scores treat a noise token as a term."),
    "mr president": ("genuine", "Fixed form of address to the chair."),
    "national restaurant stock": ("junk", "A damaged slice around the National Western Stock Show, not a name anyone uses."),
    "national western stock": ("acceptable", "The front of 'National Western Stock Show', cut to three tokens. The bigram 'national western' is gold; this trigram was not listed."),
    "ocean boulevard": ("genuine", "Fixed street name."),
    "of the": ("junk", "The highest-frequency grammatical bigram. Dependence here is English, not a domain."),
    "on the": ("junk", "Preposition plus determiner."),
    "one of the": ("junk", "A partitive frame."),
    "orange crush": ("genuine", "Fixed local name (the Orange Crush interchange), not a compositional color-plus-verb."),
    "president pro tem": ("genuine", "Fixed officer title."),
    "pro tem": ("genuine", "The short form of president pro tempore."),
    "real estate": ("genuine", "Fixed industry term."),
    "real estate master": ("genuine", "The start of a master-plan title. Kept on the gold list as that name."),
    "recreation assistant": ("genuine", "Fixed job title."),
    "restaurant stock show": ("junk", "Another broken window on the stock-show name, with 'restaurant' intruding."),
    "right utility economic": ("junk", "The middle of 'Civil Rights, Utilities, Economic Development'. The comma was tokenized away."),
    "san francisco": ("genuine", "City name."),
    "santa clara": ("genuine", "Place name."),
    "santa cruz": ("acceptable", "Place name. The gold list kept the longer 'santa cruz park' and not this bigram."),
    "santa cruz park": ("genuine", "Fixed park name."),
    "say thank you": ("acceptable", "A politeness frame, not a topic."),
    "so i": ("junk", "Discourse glue."),
    "so thank you": ("acceptable", "Politeness formula with a discourse 'so'."),
    "solid waste": ("genuine", "Fixed utility term."),
    "solid waste advisory": ("genuine", "Fixed committee name, truncated before 'committee' but still the conventional start."),
    "super bowl": ("genuine", "Fixed event name."),
    "tara rise": ("acceptable", "A street or subdivision name that NLTK's marginals ranked into the PMI top 20. Not gold-listed."),
    "task force": ("genuine", "Fixed institutional compound."),
    "texas historical commission": ("genuine", "Fixed agency name."),
    "thank you": ("acceptable", "The dominant politeness formula in council speech. Fixed, and not a domain tag."),
    "thank you again": ("acceptable", "Politeness formula plus 'again'."),
    "thank you and": ("junk", "'Thank you' plus the coordinator that starts the next clause. The third word is not part of the formula."),
    "thank you councilman": ("acceptable", "Politeness plus a title. Fixed as an address, not a topic."),
    "thank you councilmember": ("acceptable", "Politeness plus a title."),
    "thank you councilor": ("acceptable", "Politeness plus a title."),
    "thank you councilwoman": ("acceptable", "Politeness plus a title."),
    "thank you counsel": ("acceptable", "Politeness plus a mis-heard or alternate title 'counsel'."),
    "thank you counselor": ("acceptable", "Politeness plus a title."),
    "thank you for": ("acceptable", "The formula plus the preposition that introduces the reason."),
    "thank you madam": ("acceptable", "Politeness plus a gendered form of address."),
    "thank you mr": ("acceptable", "The usual bridge into 'mr president'. Gold lists the bigram 'mr president', not this trigram."),
    "thank you ms": ("acceptable", "Politeness plus a title."),
    "thank you president": ("acceptable", "Politeness plus the office."),
    "thank you so": ("acceptable", "Politeness with an intensifier starting the next bit."),
    "thank you to": ("junk", "'Thank you' plus a preposition. The third token is whatever comes next, so the trigram is not fixed."),
    "thank you very": ("junk", "'Thank you very much' cut before 'much'. The trigram is an incomplete intensifier."),
    "that we": ("junk", "Complementizer plus pronoun."),
    "that we be": ("junk", "Lemmatized 'that we are'."),
    "that we have": ("junk", "A clause opening, not a term."),
    "the city": ("acceptable", "A compositional frame that is constant in this genre. Not gold, because 'city council' and 'city of' carry the name."),
    "there be": ("junk", "Lemmatized 'there is' / 'there are'."),
    "this be": ("junk", "Lemmatized 'this is'. The tagger created a collocation that was never spoken."),
    "to thank you": ("acceptable", "The purpose clause in 'want to thank you'. Discourse, not a topic."),
    "tony frank": ("genuine", "Fixed personal name."),
    "urban renewal area": ("genuine", "Fixed planning designation."),
    "utility economic development": ("genuine", "Gold-listed as the tail of the utilities and economic-development committee name. It is institutional, and it is also a window cut out of a longer list."),
    "vice mayor lowenthal": ("genuine", "Title plus surname, the way the clerk addresses that member."),
    "vince lombardi": ("genuine", "Fixed personal name."),
    "vince lombardi trophy": ("genuine", "Fixed trophy name, the trigram that contains the bigram 'lombardi trophy'."),
    "want to": ("junk", "Verb plus infinitive marker. It combines with anything."),
    "wastewater treatment division": ("genuine", "Fixed department name."),
    "we be": ("junk", "Lemmatized 'we are'."),
    "we be go": ("junk", "Lemmatized 'we are going'."),
    "we have": ("junk", "Pronoun plus verb, no lexical term."),
    "western stock show": ("genuine", "Fixed event name (National Western Stock Show), the portion the gold list kept."),
    "would like to": ("junk", "Politeness chain, fully compositional."),
    "you know": ("acceptable", "A fixed discourse marker. Not a domain tag."),
    "you mr president": ("acceptable", "The address formula heard as 'thank you, Mr. President', without 'thank'. Gold kept 'mr president'."),
}


def bias(metric: str, label: str) -> str:
    if metric in {"pmi", "nltk_pmi"}:
        if label == "junk":
            return (
                "PMI still scores it at {score} with count {freq} because the two pieces are nearly exclusive. "
                "The measure only compares the joint probability with the product of the marginals. "
                "It does not know that a backchannel or a grammatical pair is not a tag."
            )
        if label == "acceptable":
            return (
                "PMI ranks it with count {freq} for the same reason it ranks gold terms: the marginals are small. "
                "Low-frequency bias is why this fixed expression outruns 'city council'. "
                "Leaving it off the gold list makes the precision@20 hit count a lower bound."
            )
        return (
            "Count {freq} is at or near the frequency floor, and the score {score} is high because each word barely occurs outside the pair. "
            "That is PMI's low-frequency bias. A frequent title such as 'council member' is more useful to a tagger and ranks lower."
        )
    if metric == "pmi2":
        return (
            "The underlying PMI is positive, so squaring (score {score}, count {freq}) keeps this row in the same place as plain PMI. "
            "PMI squared would also promote a large negative PMI such as 'the to', but those squared values stay far below this head. "
            "The top 20 therefore copies PMI's low-frequency bias rather than correcting it."
        )
    if metric == "pmi3":
        return (
            "Cubing a positive PMI (score {score}, count {freq}) is strictly monotone, so this row matches plain PMI exactly. "
            "PMI cubed stretches the gaps among rare exclusive pairs and does not bring high-frequency titles up."
        )
    if metric == "npmi":
        if label == "junk":
            return (
                "NPMI is essentially 1 when the joint count {freq} accounts for both marginals, which is why a backchannel ties the real names. "
                "Dividing by -log P(w1, w2) removes raw PMI's extra reward for rarity, and it does not remove exclusivity."
            )
        return (
            "NPMI score {score} at count {freq} is high because the pair covers its own marginals, not because the count is large. "
            "Normalization lets a few higher-count exclusive names ('long beach', 'domestic violence') climb past some frequency-3 pairs that raw PMI had ranked above them."
        )
    if metric in {"chi_sq", "nltk_chi_sq"}:
        if label == "junk":
            return (
                "Pearson's chi-square is non-directional. Score {score} at count {freq} says the cell is dependent, "
                "and a backchannel that never occurs apart is as dependent as a policy term. "
                "The statistic does not penalize that the way PMI's information ratio is sometimes claimed to."
            )
        return (
            "Chi-square score {score} at count {freq} is large because the off-diagonal cells are nearly empty, so the pair is far from independence. "
            "Exclusive pairs of any count saturate near N. Chi-square therefore piles rare names at the top and does not rank by how frequent a useful tag is."
        )
    if metric == "chi_sq_yates":
        if phrase_is_demonym(label):
            pass
        return (
            "Yates subtracts N/2 inside the absolute deviation before squaring, so score {score} at count {freq} is pulled down relative to the uncorrected chi-square, more so for smaller counts. "
            "The correction breaks the saturated tie at N and prefers exclusive pairs that have a bit more mass. It is still non-directional, so a backchannel remains competitive with a policy term."
        )
    if metric in {"student_t", "nltk_student_t"}:
        if label == "genuine":
            return (
                "Student's t only reaches a genuine title this far down when the count is already huge. "
                "Score {score} uses denominator sqrt(count) under a Poisson variance-equals-mean assumption, and the counts are not normal. "
                "Frequency {freq} is what put the row here."
            )
        return (
            "Student's t score {score} is large because the count is {freq}, not because the pair is a term. "
            "The Manning and Schütze form divides a frequency-scale numerator by sqrt(f), so grammatical bigrams outrank domain names. "
            "The normal sampling model behind a t statistic is not satisfied by these sparse indicators."
        )
    if metric in {"likelihood_ratio", "nltk_likelihood_ratio"}:
        if label == "genuine":
            return (
                "G^2 score {score} at count {freq} is one of the few domain hits in this top 20. "
                "The likelihood ratio still grows with sample size and is non-directional, but it is less hypnotized by frequency-3 exclusivity than PMI or Pearson's chi-square, so a repeated title can surface."
            )
        if label == "acceptable":
            return (
                "G^2 score {score} at count {freq} rewards a repeated fixed formula. "
                "Dunning's statistic behaves better than chi-square at low counts, and on this list the mass is not low: high-frequency discourse still fills most of the top 20."
            )
        return (
            "G^2 score {score} at count {freq} is large because the observed cell is far from the independence expected count and the count itself is high. "
            "The statistic does not point toward association rather than dissociation, and it does not prefer a rare technical term over 'of the'."
        )
    if metric in {"trigram_pmi", "nltk_trigram_pmi"}:
        if label == "junk":
            return (
                "Trigram PMI score {score} at count {freq} treats a three-token window as a unit. "
                "Committee lists and ASR splices produce exclusive windows that are not phrases. "
                "The same low-frequency bias as bigram PMI applies, with even sparser counts."
            )
        return (
            "Trigram PMI score {score} at count {freq} is high because the three position-specific marginals are close to the joint count. "
            "Real names survive, and so do fragments of longer names. The frequency floor of 3 is the only thing keeping hapax trigrams out of this list."
        )
    if metric == "nltk_trigram_chi_sq":
        return (
            "NLTK trigram chi-square score {score} at count {freq} again rewards exclusive triples. "
            "It tracks trigram PMI's names, and it also admits code-like junk such as agenda numbers once their cells are extreme."
        )
    if metric == "nltk_trigram_student_t":
        return (
            "Trigram t score {score} at count {freq} is the bigram t-test's frequency bias in a three-word window. "
            "Lemmatized verb chains dominate. The normal approximation is no better for trigram counts than for bigrams."
        )
    if metric == "nltk_trigram_likelihood_ratio":
        return (
            "Trigram G^2 score {score} at count {freq} collapses onto the 'thank you' family. "
            "Every extension of a very frequent bigram inherits a huge likelihood ratio. "
            "The list is non-directional dependence of one politeness formula, not a set of domain trigrams."
        )
    raise KeyError(metric)


def phrase_is_demonym(label: str) -> bool:
    return False


EXTRAS = {
    ("likelihood_ratio", "council member"): (
        " No other from-scratch metric places 'council member' in its top 20."
    ),
    ("chi_sq_yates", "cape verdean"): (
        " This is the Yates-only phrase in the eight from-scratch top-20 lists."
    ),
    ("student_t", "this be"): (
        " Among the from-scratch metrics, only the t-test promotes 'this be' into the top 20."
    ),
    ("nltk_pmi", "tara rise"): (
        " Our PMI ranks 'brook tucker' in this slot. NLTK's unigram marginals and finder.N, which counts tokens rather than bigrams, swap the two."
    ),
    ("nltk_pmi", "brook tucker"): (
        " Included because our implementation's left and right marginals differ from NLTK's raw unigram counts at sentence edges."
    ),
}


def entry_for(metric: str, phrase: str) -> dict[str, str]:
    if phrase not in FACTS:
        raise KeyError(phrase)
    label, fact = FACTS[phrase]
    if label == "genuine" and phrase not in GOLD:
        raise SystemExit(f"marked genuine but not gold: {phrase}")
    if label != "genuine" and phrase in GOLD:
        raise SystemExit(f"gold phrase not marked genuine: {phrase}")
    text = fact + " " + bias(metric, label)
    text += EXTRAS.get((metric, phrase), "")
    return {"label": label, "commentary": text}


def build_commentary(phrases_by_metric: dict[str, list[str]]) -> dict[str, dict[str, dict[str, str]]]:
    """Commentary keyed to the phrases actually ranked in each metric's top-20."""
    commentary: dict[str, dict[str, dict[str, str]]] = {}
    missing: list[str] = []
    for metric, phrases in phrases_by_metric.items():
        commentary[metric] = {}
        for phrase in phrases:
            try:
                commentary[metric][phrase] = entry_for(metric, phrase)
            except KeyError:
                missing.append(f"{metric}:{phrase}")
    if missing:
        raise SystemExit("missing facts: " + ", ".join(sorted(set(missing))))
    return commentary


def main() -> None:
    phrases_by_metric: dict[str, list[str]] = {}
    for path in sorted((ROOT / "reports").glob("top20_*.csv")):
        if path.name == "top20_overlap_jaccard.csv" or path.name.startswith("top20_unfiltered"):
            continue
        metric = path.name[len("top20_") : -len(".csv")]
        frame = pd.read_csv(path)
        phrases_by_metric[metric] = list(frame["phrase"].astype(str))
    commentary = build_commentary(phrases_by_metric)
    out = ROOT / "data/annotated/phrase_commentary.json"
    out.write_text(json.dumps(commentary, indent=2), encoding="utf-8")
    n = sum(len(v) for v in commentary.values())
    print(f"wrote {n} commentaries across {len(commentary)} metrics")


if __name__ == "__main__":
    main()
