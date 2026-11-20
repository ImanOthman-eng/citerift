"""Builds BIB_CORPUS.json: the fail-first adversarial corpus of bib-1 (owner decision D-083, item 4).

Each case is one (citation template, Stage 02 record) pair with the verdict BIBLIOGRAPHIC_SPEC.md requires, written
down from the specification before the production and reference outputs were compared. ``origin`` says where a case
comes from: ``development:<article>/<unit>`` cases copy a template and a record from development evidence (the 232 /
80 / 100 design-exposed articles and the Stage 02 index ``rw-2f116e9ffed718e6``); every other case is SYNTHETIC
(made-up names, titles and records, not Retraction Watch data). No label, adjudication or score of any campaign is
used. Run: ``python build_corpus.py`` (writes BIB_CORPUS.json next to this file).
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

GARRY_TEMPLATE = (
    "{{cite journal\n |author=Robert Garry\n |title=Influenza or not influenza: Analysis of a case of high fever that "
    "happened 2000 years ago in Biblical time – Comments\n |journal=Virology Journal\n |date=21 July 2010\n |volume=7\n"
    " |issue=1\n |page=169\n |doi=10.1186/1743-422X-7-169\n |pmid=20663162\n |pmc=2918564\n |s2cid=8124033\n"
    " |doi-access=free\n }}"
)
GARRY_RECORD = {
    "title": "Influenza or not Influenza: Analysis of a Case of High Fever That Happened 2000 Years Ago in Biblical "
    "Time",
    "authors": "Kam L E Hon;Pak C Ng;Ting F Leung",
    "journal": "Virology Journal",
    "original_year": 2010,
}
GT = "Influenza or not influenza: Analysis of a case of high fever that happened 2000 years ago in Biblical time"

# A synthetic record used by most synthetic cases.
REC = {
    "title": "Thermal Drift of Synthetic Lattice Sensors: A Field Study",
    "authors": "Mara Q Lindqvist;Tomas Oyelaran;Hana Brezinova",
    "journal": "Journal of Synthetic Instrumentation",
    "original_year": 2015,
}
T = "Thermal drift of synthetic lattice sensors: a field study"


def cite(**params: str) -> str:
    return "{{cite journal " + " ".join(f"|{k}={v}" for k, v in params.items()) + "}}"


def case(cid, category, source, record, obj, reasons=(), wiki="en", origin="synthetic", note="", **fields):
    exp = {"object": obj, "reasons": sorted(reasons), **fields}
    return {"id": cid, "category": category, "wiki": wiki, "source": source, "record": record, "expect": exp,
            "origin": origin, "note": note}  # fmt: skip


MC, CO, IN = "MATERIAL_CONFLICT", "COMPATIBLE", "INSUFFICIENT"
RA, RT, RR = "BIB_AUTHORS_DISJOINT", "BIB_TITLE_DISJOINT", "BIB_TITLE_RELATED_OBJECT"

CASES = [
    # 1. The P2 false attachment and its true original (development evidence).
    case(
        "garry-exact",
        "garry",
        GARRY_TEMPLATE,
        GARRY_RECORD,
        MC,
        [RA, RR],
        origin="development:en-27958530/un-00004",
        authors="CONFLICT",
        title_relation="CONTAINED",
        designation=True,
        note="other author; title = record title + a comment designation",
    ),
    case(
        "garry-authors-only",
        "garry",
        cite(author="Robert Garry", title=GT, journal="Virology Journal"),
        GARRY_RECORD,
        MC,
        [RA],
        authors="CONFLICT",
        title_relation="EQUAL",
        note="designation removed: the author rule alone blocks it (no suffix rule involved)",
    ),
    case(
        "garry-title-only",
        "garry",
        cite(last1="Hon", first1="K. L.", title=GT + " – Comments"),
        GARRY_RECORD,
        MC,
        [RR],
        authors="AGREE",
        title_relation="CONTAINED",
        designation=True,
        note="original authors but a comment designation outside the record title",
    ),
    case(
        "garry-true-original",
        "true_original",
        cite(
            last1="Hon",
            first1="K. L.",
            last2="Ng",
            first2="P. C.",
            last3="Leung",
            first3="T. F.",
            title=GT,
            journal="Virology Journal",
            date="2010",
            doi="10.1186/1743-422X-7-169",
        ),
        GARRY_RECORD,
        CO,
        authors="AGREE",
        title="AGREE",
        title_relation="EQUAL",
        year="SAME",
        periodical="SAME",
    ),
    case(
        "true-original-vauthors",
        "true_original",
        cite(vauthors="Hon KL, Ng PC, Leung TF", title=GT),
        GARRY_RECORD,
        CO,
        authors="AGREE",
        title_relation="EQUAL",
    ),
    # 2. Punctuation, author format, truncated authors, subtitles.
    case(
        "punct-case",
        "punctuation",
        cite(author="Lindqvist, M. Q.", title="THERMAL DRIFT OF SYNTHETIC LATTICE SENSORS — A FIELD STUDY."),
        REC,
        CO,
        authors="AGREE",
        title="AGREE",
        title_relation="EQUAL",
    ),
    case(
        "punct-markup",
        "punctuation",
        cite(
            last="Oyelaran", title="''Thermal drift'' of [[synthetic lattice]] sensors: a field&nbsp;study<!-- note -->"
        ),
        REC,
        CO,
        authors="AGREE",
        title_relation="EQUAL",
    ),
    case(
        "diacritics",
        "author_format",
        cite(last1="Brezinová", first1="H.", title=T),
        REC,
        CO,
        authors="AGREE",
        note="diacritics folded",
    ),
    case("author-inverted", "author_format", cite(author="Lindqvist, Mara Q.", title=T), REC, CO, authors="AGREE"),
    case(
        "author-initials-only",
        "author_format",
        cite(author="M. Q. L.", title=T),
        REC,
        CO,
        authors="INSUFFICIENT",
        title="AGREE",
        note="initials are not names",
    ),
    case("truncated-etal", "truncated_authors", cite(author="Lindqvist M, et al.", title=T), REC, CO, authors="AGREE"),
    case(
        "only-etal", "truncated_authors", cite(author="et al.", title=T), REC, CO, authors="INSUFFICIENT", title="AGREE"
    ),
    case(
        "subtitle-truncated",
        "subtitle",
        cite(last1="Lindqvist", title="Thermal drift of synthetic lattice sensors"),
        REC,
        CO,
        title_relation="CONTAINED",
        designation=False,
    ),
    case(
        "subtitle-extended",
        "subtitle",
        cite(last1="Lindqvist", title=T + ": results from three winters"),
        REC,
        CO,
        title_relation="CONTAINED",
        designation=False,
    ),
    case(
        "typo-overlap",
        "punctuation",
        cite(last1="Lindqvist", title="Thermal drfit of syntetic lattice sensors"),
        REC,
        CO,
        title_relation="OVERLAP",
        designation=False,
    ),
    # 3. Related objects and notices (designations outside the record title).
    case(
        "comment-other-authors",
        "comment",
        cite(author="Peter Quill", title="Comment on: " + T),
        REC,
        MC,
        [RA, RR],
        authors="CONFLICT",
        designation=True,
    ),
    case(
        "comment-same-authors",
        "comment",
        cite(last1="Lindqvist", title="Comments on " + T),
        REC,
        MC,
        [RR],
        authors="AGREE",
        designation=True,
    ),
    case(
        "reply", "reply", cite(last1="Lindqvist", title="Reply to the comment on " + T), REC, MC, [RR], designation=True
    ),
    case(
        "response-to",
        "reply",
        cite(last1="Lindqvist", title="Response to Quill: " + T),
        REC,
        MC,
        [RR],
        designation=True,
        note="phrase 'response to'",
    ),
    case(
        "editorial-genre",
        "editorial",
        cite(last1="Lindqvist", title="Editorial: " + T),
        REC,
        MC,
        [RR],
        designation=True,
        note="a genre word the record's title lacks: abstain (review A-02; a retracted editorial cited with its own "
        "title is EQUAL and unaffected)",
    ),
    case("erratum", "erratum", cite(last1="Lindqvist", title="Erratum: " + T), REC, MC, [RR], designation=True),
    case(
        "correction-to",
        "erratum",
        cite(last1="Lindqvist", title="Correction to: " + T),
        REC,
        MC,
        [RR],
        designation=True,
    ),
    case(
        "corrigendum", "erratum", cite(last1="Lindqvist", title=T + " (Corrigendum)"), REC, MC, [RR], designation=True
    ),
    case(
        "withdrawal-notice",
        "withdrawal",
        cite(last1="Lindqvist", title="Withdrawal: " + T),
        REC,
        MC,
        [RR],
        designation=True,
    ),
    case(
        "withdrawn-status",
        "withdrawal",
        cite(last1="Lindqvist", title="WITHDRAWN: " + T),
        REC,
        CO,
        designation=False,
        note="status watermark of the work itself",
    ),
    case(
        "retraction-notice",
        "retraction_notice",
        cite(title='Retraction notice to "' + T + '"'),
        REC,
        MC,
        [RR],
        authors="INSUFFICIENT",
        designation=True,
    ),
    case(
        "retracted-watermark",
        "retraction_notice",
        cite(last1="Lindqvist", title="RETRACTED ARTICLE: " + T),
        REC,
        CO,
        designation=False,
    ),
    case("eoc-notice", "eoc", cite(title="Expression of concern: " + T), REC, MC, [RR], designation=True),
    case(
        "retracted-comment-own-title",
        "comment",
        cite(last1="Lindqvist", title="Comment on the lattice debate"),
        {**REC, "title": "Comment on the lattice debate"},
        CO,
        title="AGREE",
        designation=False,
        note="a retracted comment: the designation is inside the record's own title",
    ),
    case(
        "letter-genre-dev",
        "editorial",
        "{{cite journal |journal=[[The BMJ]] |last=Murphy |first=John M. |author-link=John Murphy (branding "
        "consultant) |title=Letter: Cello scrotum |date=11 May 1974 |volume=2 |issue=5914 |page=335 |pmid=4827125 "
        "|pmc=1610985 |doi=10.1136/bmj.2.5914.335-a}}",
        {
            "title": "Cello scrotum",
            "authors": "J M Murphy",
            "journal": "BMJ: British Medical Journal",
            "original_year": 1974,
        },
        MC,
        [RR],
        authors="AGREE",
        designation=True,
        year="SAME",
        origin="development:en-21293835",
        note="stated recall cost (spec 4.2, section 9): the retracted work is itself a letter, and the citation adds "
        "the genre word 'Letter:' that its record title lacks, so the description designates a related object and "
        "abstains",
    ),
    case(
        "jasist-withdrawal-dev",
        "withdrawal",
        "{{cite journal |arxiv=1407.2137 |last1=Iorio |first1=L. |journal=Journal of the Association for Information "
        "Science and Technology |volume=65 |issue=11 |page=2375 |doi=10.1002/asi.23238 |title=''Withdrawal:'' 'A new "
        "type of misconduct in the field of the physical sciences: The case of the pseudonyms used by I. Ciufolini to "
        "anonymously criticize other people's works on arXiv' by L. Iorio |year=2014}}",
        {
            "title": "A new type of misconduct in the field of the physical sciences: The case of the pseudonyms used "
            "by I. Ciufolini to anonymously criticize other people's works on arXiv",
            "authors": "L Iorio",
            "journal": "Journal of the Association for Information Science and Technology",
            "original_year": 2014,
        },
        MC,
        [RR],
        authors="AGREE",
        designation=True,
        origin="development:en-39868218/un-00011",
        note="the evaluation-1 JASIST unit: dt-3 still decides it by D-10 (role collision) first",
    ),
    # 4. Same title, different object; same identifiers, incompatible description.
    case(
        "same-title-other-authors",
        "same_title_other_object",
        cite(author="Ines Vargas", title=T),
        REC,
        MC,
        [RA],
        title="AGREE",
    ),
    case(
        "wrong-identifier-dev",
        "incompatible_description",
        "{{استشهاد بدورية محكمة |الأخير1=Pang |الأول1=Z. P. |الأخير2=Yang |الأول2=N. |الأخير3=Vierbuchen |الأول3=T. "
        "|عنوان=Induction of human neuronal cells by defined transcription factors |صحيفة=Cell |المجلد=145 "
        "|العدد=7 |صفحات=1010–1011 |تاريخ=2011}}",
        {
            "title": "Directed Conversion of Alzheimer's Disease Patient Skin Fibroblasts Into Functional Neurons",
            "authors": "Liang Qiang;Ryousuke Fujita;Toru Yamashita;Sergio Angulo;Herve Rhinn;David Rhee;Claudia Doege;"
            "Lily Chau;William B. Vanti;Herman Moreno;Asa Abeliovich",
            "journal": "Cell",
            "original_year": 2011,
        },
        MC,
        [RA],
        wiki="ar",
        authors="CONFLICT",
        title_relation="OVERLAP",
        origin="development:ar-10305362",
        note="titles share only function words (OVERLAP, not DISJOINT); the authors decide",
    ),
    case(
        "same-authors-disjoint-title",
        "incompatible_description",
        cite(last1="Lindqvist", title="Coastal erosion budgets"),
        REC,
        MC,
        [RT],
        authors="AGREE",
        title_relation="DISJOINT",
    ),
    case(
        "disjoint-title-no-authors",
        "incompatible_description",
        cite(title="Coastal erosion budgets"),
        REC,
        MC,
        [RT],
        authors="INSUFFICIENT",
        title_relation="DISJOINT",
    ),
    case(
        "chapter-in-book-dev",
        "true_original",
        "{{استشهاد بدورية محكمة |الأخير1=Ahovuo-Saloranta |الأول1=A. |الأخير2=Rautakorpi |الفصل=Antibiotics for "
        "acute maxillary sinusitis |عنوان=Cochrane Database of Systematic Reviews |سنة=2008 "
        "|doi=10.1002/14651858.CD000243.pub2}}",
        {
            "title": "Antibiotics for acute maxillary sinusitis (Pub 2)",
            "authors": "Anneli Ahovuo Saloranta;Ulla Maija "
            "Rautakorpi;Oleg V Borisenko;Helena Liira;John W Williams Jr;Marjukka Makela",
            "journal": "Cochrane Database of Systematic Reviews",
            "original_year": 2008,
        },
        CO,
        wiki="ar",
        authors="AGREE",
        title_relation="CONTAINED",
        origin="development:ar-311750-a1",
        note="the work's title is in the chapter parameter; the title parameter names the database",
    ),
    # 5. Malformed, missing and insufficient fields.
    case(
        "malformed-title-markup-only",
        "malformed",
        cite(title="{{lang|fr|}}<!-- -->", author="<!-- -->"),
        REC,
        IN,
        authors="INSUFFICIENT",
        title="INSUFFICIENT",
        title_relation="MISSING",
    ),
    case(
        "missing-title",
        "missing_title",
        cite(last1="Quill", journal="Journal of Synthetic Instrumentation"),
        REC,
        MC,
        [RA],
        title_relation="MISSING",
        periodical="SAME",
    ),
    case(
        "missing-title-agree",
        "missing_title",
        cite(last1="Oyelaran"),
        REC,
        CO,
        authors="AGREE",
        title_relation="MISSING",
    ),
    case("missing-author", "missing_author", cite(title=T), REC, CO, authors="INSUFFICIENT", title="AGREE"),
    case(
        "no-fields",
        "insufficient",
        cite(doi="10.5555/synthetic.1"),
        REC,
        IN,
        authors="INSUFFICIENT",
        title_relation="MISSING",
    ),
    case(
        "not-a-template",
        "insufficient",
        "Lindqvist M. Thermal drift. doi:10.5555/synthetic.1",
        REC,
        IN,
        cited_none=True,
        note="free text: no cited object",
    ),
    case("two-templates", "insufficient", cite(title=T) + " " + cite(title=T), REC, IN, cited_none=True),
    case(
        "oversized-title",
        "malformed",
        cite(last1="Quill", title="x" * 4092),
        REC,
        IN,
        cited_none=True,
        note="spec 2.1 step 6: 4,097 code points in all, above the size bound: no cited object (never truncated)",
    ),
    case(
        "too-many-authors",
        "malformed",
        cite(title="Coastal erosion budgets", **{f"last{i}": f"Q{i}" for i in range(1, 66)}),
        REC,
        IN,
        cited_none=True,
        note="spec 2.1 step 6: 65 author values",
    ),
    case(
        "at-the-size-bound",
        "malformed",
        cite(last1="Quill", title="x" * 4091),
        REC,
        MC,
        [RA, RT],
        authors="CONFLICT",
        title_relation="DISJOINT",
        note="spec 2.1 step 6: exactly 4,096 code points in all is described",
    ),
    case(
        "sixty-four-authors",
        "malformed",
        cite(title=T, **{f"last{i}": ("Lindqvist", "Oyelaran", "Brezinova")[i % 3] for i in range(1, 65)}),
        REC,
        CO,
        authors="AGREE",
        note="spec 2.1 step 6: 64 author values are described; every value names a record author (spec 4.1)",
    ),
    case(
        "sixty-four-authors-last-stranger",
        "malformed",
        cite(
            title=T,
            **{f"last{i}": ("Lindqvist", "Oyelaran", "Brezinova")[i % 3] for i in range(1, 64)},
            last64="Quill",
        ),
        REC,
        MC,
        [RA],
        authors="CONFLICT",
        note="spec 2.1 step 6 and 4.1: the 64th value is described and names no record author",
    ),
    case(
        "record-malformed",
        "insufficient",
        cite(last1="Quill", title=T),
        {"title": 5, "authors": ["Mara Lindqvist"], "journal": None, "original_year": True},
        IN,
        authors="INSUFFICIENT",
        title_relation="MISSING",
        year="INSUFFICIENT",
    ),
    case(
        "duplicate-param-last-wins",
        "malformed",
        cite(title="Coastal erosion budgets", last1="Lindqvist") + "",
        REC,
        MC,
        [RT],
        note="title given once; contrast with the next case",
    ),
    case(
        "duplicate-param-overrides",
        "malformed",
        "{{cite journal |title=Coastal erosion budgets |last1=Lindqvist |title=" + T + "}}",
        REC,
        CO,
        title="AGREE",
        note="the later duplicate replaces the earlier value",
    ),
    # 6. Arabic.
    case(
        "arabic-title-latin-record",
        "arabic",
        "{{استشهاد بدورية محكمة |عنوان=الانجراف الحراري في المستشعرات |الأخير1=لينكفيست}}",
        REC,
        IN,
        wiki="ar",
        authors="INSUFFICIENT",
        title_relation="INCOMPARABLE",
    ),
    case(
        "arabic-params-latin-values",
        "arabic",
        "{{استشهاد بدورية محكمة |عنوان=" + T + " |الأخير1=Lindqvist "
        "|صحيفة=Journal of Synthetic Instrumentation |سنة=2015}}",
        REC,
        CO,
        wiki="ar",
        authors="AGREE",
        title="AGREE",
        year="SAME",
        periodical="SAME",
    ),
    case(
        "arabic-designation",
        "arabic",
        "{{استشهاد بدورية محكمة |عنوان=تعليق على " + T + " |الأخير1=Lindqvist}}",
        REC,
        MC,
        [RR],
        wiki="ar",
        designation=True,
        note="Arabic 'comment on' before the record title",
    ),
    case(
        "arabic-clitic-designation",
        "arabic",
        "{{استشهاد بدورية محكمة |عنوان=والرد " + T + " |الأخير1=Lindqvist}}",
        REC,
        CO,
        wiki="ar",
        designation=False,
        note="known limit: a clitic-prefixed word is not recognized",
    ),
    case(
        "arabic-indic-year",
        "arabic",
        "{{استشهاد بدورية محكمة |عنوان=" + T + " |تاريخ=٢٠١٥}}",
        REC,
        CO,
        wiki="ar",
        year="INSUFFICIENT",
    ),
    # 7. Stated recall costs (fail closed).
    case(
        "transliteration",
        "recall_cost",
        cite(author="Alharbi", title=T),
        {**REC, "authors": "Saad Al Harbi"},
        MC,
        [RA],
        note="known recall cost: transliteration variants",
    ),
    case(
        "corporate-author",
        "recall_cost",
        cite(author="Synthetic Sensor Consortium", title=T),
        REC,
        MC,
        [RA],
        note="known recall cost: a corporate author in an author parameter",
    ),
    # 8. Reviewer findings of the final cycle (A-01, A-02, A-04, A-05, E-01, E-02): written from the amended spec.
    case(
        "markup-snd-boundary",
        "comment",
        cite(last1="Lindqvist", title=T + "{{snd}}Comments"),
        REC,
        MC,
        [RR],
        authors="AGREE",
        title_relation="CONTAINED",
        designation=True,
        note="A-01: a removed template is a word boundary (spec 2.1 step 4), so 'Comments' stays a word",
    ),
    case(
        "markup-pipe-template-boundary",
        "reply",
        cite(last1="Lindqvist", title="Thermal drift{{!}}Reply"),
        REC,
        MC,
        [RR],
        authors="AGREE",
        title_relation="OVERLAP",
        designation=True,
        note="A-01: {{!}} is a word boundary; 'Reply' is an extra word the record title lacks",
    ),
    case(
        "markup-br-boundary",
        "comment",
        cite(last1="Lindqvist", title=T + "<br/>Comments"),
        REC,
        MC,
        [RR],
        authors="AGREE",
        designation=True,
        note="A-01: a tag is a word boundary",
    ),
    case(
        "markup-ref-content-kept",
        "comment",
        cite(last1="Lindqvist", title=T + "<ref>Comments</ref>"),
        REC,
        MC,
        [RR],
        authors="AGREE",
        title_relation="CONTAINED",
        designation=True,
        note="the pinned parser's strip_code keeps a tag's contents (an expectation that the <ref> text is dropped was "
        "wrong and corrected after the first run), and the tag is a word boundary: 'Comments' designates, fail closed",
    ),
    case(
        "lone-surrogate-entity",
        "malformed",
        cite(last1="Lindqvist", title=T + " &#xD800;"),
        REC,
        IN,
        cited_none=True,
        note="E-01: a numeric entity that decodes to a lone surrogate is not Unicode text (spec 2.1 step 4)",
    ),
    case(
        "oversized-source",
        "malformed",
        cite(last1="Lindqvist", title=T, quote="x" * 16400),
        REC,
        IN,
        cited_none=True,
        note="E-02: a template source over 16,384 code points is not parsed (spec 2.1 step 1)",
    ),
    case(
        "given-name-collision",
        "incompatible_description",
        cite(author="Tomas Quill", title=T),
        REC,
        MC,
        [RA],
        authors="CONFLICT",
        note="A-02: the record given name 'Tomas' is not a surname word (spec 3, S_R)",
    ),
    case(
        "vancouver-initials-never-count",
        "incompatible_description",
        cite(vauthors="Quill ML", title=T),
        REC,
        MC,
        [RA],
        authors="CONFLICT",
        note="A-02: cited initials 'ML' are removed and never match the record (spec 3)",
    ),
    case(
        "particle-collision",
        "incompatible_description",
        cite(author="Al-Saud", title=T),
        {**REC, "authors": "Hassan Al Harbi"},
        MC,
        [RA],
        authors="CONFLICT",
        note="A-02: the shared particle 'al' says nothing about the person (spec 3, NP)",
    ),
    case(
        "coauthor-list-one-coincident-name",
        "comment",
        cite(last1="Lindqvist", last2="Quill", title=T),
        REC,
        MC,
        [RA],
        authors="CONFLICT",
        note="A-02: every comparable cited value must name a record author (spec 4.1)",
    ),
    case(
        "re-prefix",
        "reply",
        cite(last1="Lindqvist", title="Re: " + T),
        REC,
        MC,
        [RR],
        designation=True,
        note="A-02: 'Re:' of an answer is in the lexicon",
    ),
    case(
        "authors-response",
        "reply",
        cite(last1="Lindqvist", title="Authors' response to: " + T),
        REC,
        MC,
        [RR],
        designation=True,
        note="A-02: 'response' is in the lexicon",
    ),
    case(
        "plural-corrigenda",
        "erratum",
        cite(last1="Lindqvist", title="Corrigenda: " + T),
        REC,
        MC,
        [RR],
        designation=True,
        note="A-05: every English lexicon word is listed in the singular and the plural",
    ),
    case(
        "designation-in-second-title-value",
        "comment",
        cite(last1="Lindqvist", title=T, chapter="Comments on thermal drift"),
        REC,
        MC,
        [RR],
        title_relation="EQUAL",
        designation=True,
        note="A-04: every CONTAINED or OVERLAP value is checked for designation, not only the chosen value",
    ),
    case(
        "chapter-erratum-disjoint",
        "erratum",
        cite(last1="Lindqvist", title=T, chapter="Erratum"),
        REC,
        CO,
        title_relation="EQUAL",
        designation=False,
        note="stated limit (spec section 9): a value DISJOINT from the record title never designates",
    ),
    case(
        "collaboration-param-ignored",
        "author_format",
        cite(collaboration="Synthetic Sensor Consortium", title=T),
        REC,
        CO,
        authors="INSUFFICIENT",
    ),
]


def main() -> None:
    ids = [c["id"] for c in CASES]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate case id")
    doc = {
        "format": "citerift-bib-corpus/1",
        "specification": "docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC.md (bib-1)",
        "label": "SYNTHETIC unless origin names development evidence; never evaluation data",
        "cases": CASES,
    }
    (HERE / "BIB_CORPUS.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(CASES), "cases")


if __name__ == "__main__":
    main()
