"""One-time build script: turns the raw frequency tables below into
data/frequency_library.json for the app to load. Covers three separate
frequency systems, each with distinct provenance - kept clearly labeled
(the "system" field on each entry) rather than blended together, since
they come from different traditions and shouldn't be presented as one
undifferentiated list:

1. CAFL (Consolidated Annotated Frequency List) - the publicly available,
   decades-old practitioner-compiled reference (Jim Bare, Dan Tracy, and
   others), gathered per royalrife.com/freq.html, itself drawing on the
   same public CAFL that essentially every Rife-frequency tool - including
   the Z-App the user referenced - is built on. This is NOT Rife's original
   1930s RF lab measurements (those are ultra-high radio frequencies,
   139kHz-1.6MHz, physically impossible to reproduce as an audio file) -
   it's the real-world, audio-range standard the wellness-frequency
   community actually uses.

2. Solfeggio frequencies - the 9-tone scale (174-963 Hz) widely used in
   sound healing for emotional/spiritual states, cross-checked against two
   independent sources (aurahealth.io, miraclefrequencies.org) for the
   standard meaning of each tone.

3. Chakra frequencies - the 7 chakras mapped to Solfeggio tones, verified
   consistent across two independent sources (eyemindspirit.com,
   miraclefrequencies.org). Both sources note an alternative
   planetary-orbital-tone chakra system also circulates; this uses the
   Solfeggio mapping, the one most widely used in sound healing practice.

Run once: python3 build_cafl_data.py
"""
import json
import re

# name, category, raw frequency string (kept verbatim as source of truth)
RAW = [
    ("Abdominal Pain", "Pain & Inflammation", "5000, 10000"),
    ("General Inflammation", "Pain & Inflammation", "40, 95, 250, 500, 625, 802, 1000, 2720, 3176, 10000"),
    ("Abdominal Cramps", "Digestive & Gut", "72, 95, 190, 304"),
    ("Acne", "Skin & Hair", "727, 787, 880, 5000"),
    ("Adenoids", "Ears, Eyes, Mouth & Throat", "20, 727, 787, 800, 880"),
    ("AIDS", "Immune & Infection", "727, 787, 880, 2489, 5000, 31000, 31750, 34750"),
    ("Allergies", "Immune & Infection", "3, 20, 125, 727, 787, 880, 5000, 10000"),
    ("Alopecia (Hair Loss)", "Skin & Hair", "727, 787, 880, 5000, 10000"),
    ("Anemia", "Cardiovascular & Circulation", "5000"),
    ("Aneurysm", "Cardiovascular & Circulation", "20"),
    ("Anxiety", "Mental & Emotional", "304, 6130"),
    ("Appendicitis", "Digestive & Gut", "727, 787, 880"),
    ("Arteriosclerosis", "Cardiovascular & Circulation", "20, 727, 787, 880, 5000, 10000"),
    ("Arthritis - General", "Musculoskeletal", "727, 784, 787, 800, 880, 1550, 1552, 2720, 4200, 5000, 10000"),
    ("Joint Inflammation", "Musculoskeletal", "20, 40, 95, 250, 500, 625, 727, 787, 880, 1550, 2720, 3176, 10000"),
    ("Asthma", "Respiratory", "727, 787, 880, 1234, 3672, 7344, 5000, 10000"),
    ("Athlete's Foot", "Skin & Hair", "400, 727, 784, 787, 880, 5000, 10000"),
    ("Backache", "Musculoskeletal", "727, 787, 880, 10000"),
    ("Bad Teeth", "Ears, Eyes, Mouth & Throat", "400, 727, 787, 880, 5000, 10000"),
    ("Brain", "Nervous System & Brain", "20, 1000, 2000"),
    ("Brain Waves (Alpha)", "Brainwave States", "8-12"),
    ("Brain Waves (Beta)", "Brainwave States", "12-30"),
    ("Brain Waves (Delta)", "Brainwave States", "4 and lower"),
    ("Brain Waves (Theta)", "Brainwave States", "4-8"),
    ("Bronchitis", "Respiratory", "727, 880, 1234"),
    ("Bruises", "Pain & Inflammation", "10000"),
    ("Burns", "Pain & Inflammation", "727, 787, 880, 10000"),
    ("Cancer, Breast", "Immune & Infection", "20, 465, 660, 665, 690, 727, 740, 787, 800, 880, 1840, 1998, 2008, 2128, 2876, 5000, 10000"),
    ("Cancer, Carcinoma", "Immune & Infection", "20, 120, 333, 452, 464, 660, 666, 690, 683, 728, 740, 784, 787, 794, 800, 880, 1560, 1577, 1840, 1998, 2008, 2050, 2084, 2128, 2182, 2720, 2876, 3176, 5000, 6064, 10000, 304"),
    ("Cancer, Leukemia", "Immune & Infection", "2128, 2008, 880, 787, 727, 690, 666, 590, 10000, 1850, 450, 440, 428, 14, 15, 2030, 465"),
    ("Cancer, Sarcoma", "Immune & Infection", "20, 465, 660, 665, 690, 727, 740, 787, 800, 880, 979, 1840, 1998, 2004, 2008, 2012, 2128, 3672, 5000, 7760, 10000"),
    ("Candida Albicans", "Parasites & Fungal", "254, 414, 450, 465"),
    ("Cerebral Palsy", "Nervous System & Brain", "727, 787, 880, 10000"),
    ("Chlamydia", "Immune & Infection", "430, 620, 866, 2213"),
    ("Chronic Fatigue Syndrome", "Hormonal & Metabolic", "120, 424, 465, 660, 665, 727, 787, 880, 1550, 2128"),
    ("Cirrhosis", "Digestive & Gut", "727, 787, 880, 10000"),
    ("Colic", "Digestive & Gut", "727, 787, 800, 880"),
    ("Colitis", "Digestive & Gut", "727, 787, 800, 880, 10000"),
    ("Constipation", "Digestive & Gut", "727, 787, 800, 880"),
    ("Convulsions", "Nervous System & Brain", "727, 787, 880, 5000, 10000"),
    ("Coryza (Nose Disorder)", "Respiratory", "727, 787, 880"),
    ("Cystitis", "Reproductive & Urinary", "727, 787, 800, 880"),
    ("Dandruff, Scales", "Skin & Hair", "727, 787, 880, 5000"),
    ("Deafness", "Ears, Eyes, Mouth & Throat", "20, 800, 10000"),
    ("Depression", "Mental & Emotional", "664, 764"),
    ("Diabetes", "Hormonal & Metabolic", "20, 48, 72, 95, 125, 302, 444, 450, 465, 666, 690, 727, 787, 800, 880, 1550, 1850, 1865, 2008, 2128, 4200, 5000, 10000"),
    ("Diarrhea", "Digestive & Gut", "727, 787, 800, 880"),
    ("Diphtheria", "Immune & Infection", "20, 727, 787, 880"),
    ("Dysentery", "Digestive & Gut", "727, 787, 800, 880"),
    ("Dysmenorrhea", "Reproductive & Urinary", "727, 787, 800, 880"),
    ("Dyspepsia (Indigestion)", "Digestive & Gut", "727, 787, 800, 880"),
    ("E. Coli", "Immune & Infection", "799-804"),
    ("Eczema", "Skin & Hair", "727, 787, 5000"),
    ("Edema (Water Retention)", "Cardiovascular & Circulation", "727, 787, 880"),
    ("Epilepsy", "Nervous System & Brain", "20, 120, 727, 787, 880"),
    ("Epstein-Barr", "Immune & Infection", "660, 665, 690, 727, 787"),
    ("Eye, Cataract", "Ears, Eyes, Mouth & Throat", "727, 784, 787, 880, 1600, 5000, 10000"),
    ("Eye, Glaucoma", "Ears, Eyes, Mouth & Throat", "727, 787, 880, 1600, 5000, 10000"),
    ("Fever (all kinds)", "Immune & Infection", "20, 727, 787, 880, 5000, 10000"),
    ("Fibromyalgia", "Musculoskeletal", "120, 140, 304, 464, 728, 800, 880, 2489, 3176, 5000, 6000, 9000"),
    ("Flu", "Immune & Infection", "727, 770, 776, 780, 787, 800, 880, 965, 5375, 7760, 7766, 8000, 8198-8218, 8250, 8700"),
    ("Food Poisoning", "Digestive & Gut", "727, 787, 880, 10000"),
    ("Fungus", "Parasites & Fungal", "333, 450, 465, 665, 690, 727, 784, 880, 1550, 1654"),
    ("Gastritis", "Digestive & Gut", "20, 727, 787, 880, 10000"),
    ("Giardia", "Parasites & Fungal", "1943"),
    ("Gonorrhea", "Reproductive & Urinary", "600, 650, 660, 700, 712"),
    ("Gout", "Musculoskeletal", "20, 10000"),
    ("Hay Fever", "Respiratory", "727, 787, 880, 5000"),
    ("Headaches", "Pain & Inflammation", "20, 144, 160, 304, 520, 727, 787, 880, 10000"),
    ("Heart, Angina Pectoris", "Cardiovascular & Circulation", "5000"),
    ("Heart, Tachycardia", "Cardiovascular & Circulation", "5000"),
    ("Hemorrhoids", "Digestive & Gut", "20, 727, 800, 880"),
    ("Hepatitis A", "Immune & Infection", "321, 346, 414, 423, 487, 558, 578, 693, 717, 786, 878, 3220"),
    ("Hepatitis B", "Immune & Infection", "334, 433, 477, 574, 752, 767, 779, 869, 876"),
    ("Herpes, General", "Immune & Infection", "464, 1488, 1489, 1500, 1550, 1577, 1900"),
    ("Herpes, Genital", "Reproductive & Urinary", "141, 171, 440, 590, 660, 878, 898, 1175, 5310"),
    ("Herpes Zoster", "Immune & Infection", "664, 787, 802, 880, 914, 1500, 1600, 2170, 3343"),
    ("High Blood Pressure", "Cardiovascular & Circulation", "20, 304, 727, 880, 10000"),
    ("Hives (Urticaria)", "Skin & Hair", "727, 787, 880, 1800, 5000"),
    ("Insomnia", "Mental & Emotional", "727, 787, 880, 10000"),
    ("Influenza", "Immune & Infection", "727, 770, 776, 780, 787, 800, 880, 5375, 7760, 8000, 8250"),
    ("Intestines, Spasms", "Digestive & Gut", "5000"),
    ("Intestines, Inflammation", "Digestive & Gut", "20, 727, 787, 800, 880, 5000, 10000"),
    ("Kidneys", "Reproductive & Urinary", "8, 9.2, 20, 248, 440, 727, 787, 880, 1600, 1865, 10000"),
    ("Leprosy", "Immune & Infection", "600, 727, 787, 880, 10000"),
    ("Leukorrhea", "Reproductive & Urinary", "465, 727, 787, 880"),
    ("Lyme Disease", "Immune & Infection", "312, 345, 432, 484-504, 592-634, 690, 785-795, 800, 864, 1590-1640"),
    ("Lupus (SLE)", "Immune & Infection", "304, 633, 664, 702, 784, 802, 880, 1552, 2008, 2125, 2128, 2180, 2489, 3612"),
    ("Lymph Glands", "Immune & Infection", "10, 440, 880"),
    ("Malaria", "Immune & Infection", "20, 728, 787, 880"),
    ("Measles", "Immune & Infection", "20, 727, 787, 880"),
    ("Meningitis", "Nervous System & Brain", "20, 5000"),
    ("Migraine", "Pain & Inflammation", "20, 727, 787, 880, 5000"),
    ("Multiple Sclerosis", "Nervous System & Brain", "20, 166, 218, 224, 317, 470, 727, 787, 807, 880, 5000"),
    ("Mumps", "Immune & Infection", "152, 242, 642, 674, 727, 787, 880, 922"),
    ("Muscle Repair", "Musculoskeletal", "120, 240, 5000"),
    ("Muscular Dystrophy", "Musculoskeletal", "5000"),
    ("Nausea", "Digestive & Gut", "72, 95, 190, 304, 727, 787, 880, 5000"),
    ("Neuritis", "Nervous System & Brain", "727, 787, 880, 5000, 10000"),
    ("Neurosis", "Mental & Emotional", "727, 787, 880, 5000, 10000"),
    ("Nicotine Poisoning", "Detox & Vitality", "10000"),
    ("Obesity", "Hormonal & Metabolic", "10000"),
    ("Weight Loss / Metabolism Support", "Hormonal & Metabolic", "20, 465, 727, 787, 880, 5000, 10000"),
    ("Peri-Menopause", "Hormonal & Metabolic", "20, 444, 465, 727, 787, 880, 10000"),
    ("Menopause", "Hormonal & Metabolic", "20, 444, 465, 727, 787, 880, 5000, 10000"),
    ("Pancreas", "Hormonal & Metabolic", "440, 465, 600, 624, 648, 728, 784, 787, 880, 1552, 2128, 5000, 10000"),
    ("Parasites, General", "Parasites & Fungal", "20, 47, 60, 64, 72, 96, 112, 120, 125, 128, 152, 240, 334, 422, 442, 465, 524, 642, 644, 651, 669, 666, 676, 688, 690, 712, 728, 732, 740, 751, 770, 780, 784, 787, 800, 802, 854, 880, 1360, 1550, 1552, 1840, 1862, 1864, 1998, 2008, 2112, 2128, 3176, 4412, 10000"),
    ("Parkinson's", "Nervous System & Brain", "6000"),
    ("Pneumonia", "Respiratory", "20, 727, 770-780, 787, 800, 880, 5000, 10000"),
    ("Prostate Gland", "Reproductive & Urinary", "9.4, 20, 404, 664, 727, 1000, 2000, 2008, 2128, 2720, 5000"),
    ("Psoriasis", "Skin & Hair", "20, 64, 96, 104, 112, 727, 787, 880, 5000"),
    ("Pyorrhea", "Ears, Eyes, Mouth & Throat", "20, 727, 787"),
    ("Rheumatism", "Musculoskeletal", "727, 787, 880, 10000"),
    ("Sinusitis", "Respiratory", "20, 160, 320, 741, 952, 727, 776, 1550"),
    ("Smallpox", "Immune & Infection", "20, 727, 787, 880"),
    ("Sore Throat", "Ears, Eyes, Mouth & Throat", "727, 787, 880"),
    ("Staph Infections", "Immune & Infection", "727, 725-730, 787, 880, 885"),
    ("Streptococcus", "Immune & Infection", "875-885, 880"),
    ("Stroke", "Cardiovascular & Circulation", "3, 20, 230, 5000, 10000"),
    ("Syphilis", "Reproductive & Urinary", "20, 600, 625, 650, 700"),
    ("Tetanus", "Immune & Infection", "20, 120, 400, 727, 787, 880"),
    ("Tinnitus", "Ears, Eyes, Mouth & Throat", "20, 727, 784, 787, 880"),
    ("Tonsillitis", "Ears, Eyes, Mouth & Throat", "20, 727, 787, 880"),
    ("Tuberculosis", "Respiratory", "20, 800, 1550"),
    ("Tuberculosis Rod", "Respiratory", "216, 666, 690, 740, 799, 802, 803, 804, 1840"),
    ("Typhoid Fever", "Immune & Infection", "20, 690, 712, 1500-1600, 1570, 1862, 1865"),
    ("Ulcers, Duodenal", "Digestive & Gut", "727, 880, 10000"),
    ("Ulcers, Most", "Digestive & Gut", "664, 727, 776, 787, 800, 832, 880"),
    ("Warts, Plantar", "Skin & Hair", "915, 918"),
    ("Whooping Cough", "Respiratory", "20, 727, 787, 880"),
    ("Worms, Round", "Parasites & Fungal", "20, 104, 120, 240, 332, 422, 688, 721, 942, 1360, 3212"),
]

# General/vitality catch-alls that are extremely common across CAFL protocols -
# worth their own entries since they're often used standalone as a "general
# tune-up" rather than tied to one specific condition.
RAW += [
    ("General Vitality / Immune Support", "Detox & Vitality", "20, 727, 787, 880, 5000, 10000"),
    ("General Detoxification", "Detox & Vitality", "20, 440, 880, 5000, 10000"),
    ("General Pain Relief", "Pain & Inflammation", "304, 727, 787, 880, 10000"),
    ("General Relaxation", "Mental & Emotional", "10, 304, 727, 787"),
]

# Solfeggio frequencies: name carries the traditional meaning directly (the
# thing people actually search for - "liberation from fear", not just a
# number), category groups them together for browsing.
RAW_SOLFEGGIO = [
    ("174 Hz - Pain Relief & Security", "Emotional & Spiritual (Solfeggio)", "174"),
    ("285 Hz - Quantum Cognition & Healing", "Emotional & Spiritual (Solfeggio)", "285"),
    ("396 Hz - Liberating Guilt & Fear", "Emotional & Spiritual (Solfeggio)", "396"),
    ("417 Hz - Facilitating Change", "Emotional & Spiritual (Solfeggio)", "417"),
    ("528 Hz - Transformation & Miracles (Love Frequency)", "Emotional & Spiritual (Solfeggio)", "528"),
    ("639 Hz - Connecting & Relationships", "Emotional & Spiritual (Solfeggio)", "639"),
    ("741 Hz - Awakening Intuition & Expression", "Emotional & Spiritual (Solfeggio)", "741"),
    ("852 Hz - Returning to Spiritual Order", "Emotional & Spiritual (Solfeggio)", "852"),
    ("963 Hz - Divine Consciousness", "Emotional & Spiritual (Solfeggio)", "963"),
]

# Chakra frequencies: the 7 chakras mapped to Solfeggio tones (the mapping
# verified consistent across two independent sources - see module docstring).
RAW_CHAKRA = [
    ("Root Chakra - Safety & Grounding", "Chakras", "396"),
    ("Sacral Chakra - Creativity & Flow", "Chakras", "417"),
    ("Solar Plexus Chakra - Confidence & Will", "Chakras", "528"),
    ("Heart Chakra - Love & Connection", "Chakras", "639"),
    ("Throat Chakra - Truth & Expression", "Chakras", "741"),
    ("Third Eye Chakra - Intuition & Insight", "Chakras", "852"),
    ("Crown Chakra - Connection to Source", "Chakras", "963"),
]


def parse_frequencies(raw: str):
    """Returns (list_of_playable_hz, display_string). Ranges ('484-504') are
    reduced to their midpoint for playback but the original range is kept in
    the display string for transparency. Non-numeric entries ('4 and lower')
    are handled as a fixed low value with the original text preserved."""
    display = raw.strip()
    tokens = [t.strip() for t in raw.split(",")]
    values = []
    for tok in tokens:
        m = re.match(r"^([\d.]+)\s*-\s*([\d.]+)$", tok)
        if m:
            lo, hi = float(m.group(1)), float(m.group(2))
            values.append(round((lo + hi) / 2, 2))
            continue
        m2 = re.match(r"^([\d.]+)$", tok)
        if m2:
            values.append(float(m2.group(1)))
            continue
        m3 = re.match(r"^([\d.]+)\s+and\s+lower$", tok, re.IGNORECASE)
        if m3:
            values.append(float(m3.group(1)))
            continue
        # unparseable token - skip it from playback but it stays visible in display
    return values, display


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s


def build_entries(rows, system, seen_slugs, entries):
    for name, category, raw in rows:
        values, display = parse_frequencies(raw)
        slug = slugify(name)
        base_slug = slug
        i = 2
        while slug in seen_slugs:
            slug = f"{base_slug}-{i}"
            i += 1
        seen_slugs.add(slug)
        entries.append({
            "slug": slug,
            "name": name,
            "category": category,
            "system": system,
            "frequencies_hz": values,
            "frequencies_display": display,
        })


def main():
    entries = []
    seen_slugs = set()
    build_entries(RAW, "CAFL", seen_slugs, entries)
    build_entries(RAW_SOLFEGGIO, "Solfeggio", seen_slugs, entries)
    build_entries(RAW_CHAKRA, "Chakra", seen_slugs, entries)

    entries.sort(key=lambda e: (e["category"], e["name"]))

    out = {
        "source": "Three frequency systems, each labeled with its own "
                   "provenance: CAFL (Consolidated Annotated Frequency "
                   "List) - a publicly available, decades-old "
                   "practitioner-compiled reference (Jim Bare, Dan Tracy, "
                   "and others), NOT Dr. Rife's original 1930s "
                   "radio-frequency lab measurements, but the audio-range "
                   "standard used by virtually every practical "
                   "Rife-frequency tool. Solfeggio - the traditional 9-tone "
                   "scale used in sound healing for emotional/spiritual "
                   "states. Chakra - the 7 chakras mapped to Solfeggio "
                   "tones, cross-checked across independent sources.",
        "disclaimer": "For wellness/experimental use. These frequency "
                       "associations come from historical practitioner "
                       "compilations and traditional sound-healing "
                       "references, not clinical trials - nothing here is "
                       "a medical claim or a substitute for medical care.",
        "entries": entries,
    }

    with open("data/frequency_library.json", "w") as f:
        json.dump(out, f, indent=2)

    by_system = {}
    for e in entries:
        by_system.setdefault(e["system"], 0)
        by_system[e["system"]] += 1

    print(f"Wrote {len(entries)} entries across "
          f"{len(set(e['category'] for e in entries))} categories.")
    for sys_name, count in sorted(by_system.items()):
        print(f"  {sys_name}: {count}")


if __name__ == "__main__":
    main()
