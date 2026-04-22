"""
Corpus selection for LLEE dual-corpus experiment.

Segment library covering 6 writing styles:
  - Victorian fairy tale (Aladdin)
  - Gothic atmospheric (Poe)
  - Cosmic horror (Lovecraft)
  - Detective dialogue (Christie)
  - AI light novel (Sakakibara Kaito)
  - AI 2nd-person sensory (Karl)

Phase 0.5 stability test uses all segments.
Phase 1 uses subsets grouped by style and density.
"""

# ─── Corpus inventory ─────────────────────────────────────────────────────────
#
# Human-authored:
#   Aladdin starter (51 lines, 5279w) — sparse fairy tale
#   Aladdin light-origin (235 lines, 5356w) — richer fairy tale
#   Poe Vol.2 (10345 lines, 95210w) — gothic atmospheric
#   Cask of Amontillado (370 lines, 2483w) — unreliable narrator, gothic
#   Call of Cthulhu (1253 lines, 12134w) — cosmic horror, philosophical
#   Roger Ackroyd (10725 lines, 70909w) — detective, unreliable narrator
#   The Missing Will (445 lines, 3417w) — short detective
#   Secret of Chimneys (11515 lines, 74778w) — adventure mystery
#
# AI-generated:
#   Sakakibara Kaito full (928 lines, 8665w) — time-loop light novel
#   Sakakibara Kaito starter (200 lines, 1520w) — same story, compressed
#   Karl (66 lines, 1638w) — 2nd person, extreme sensory, supernatural
#
# ─── Alignment strategy ───────────────────────────────────────────────────────
#
# Dual-corpus pairs (same story, different detail):
#   Pair 1: Sakakibara full vs starter (word ratio 5.7, Gate 0 pass)
#   Pair 2: Aladdin light-origin vs starter (word ratio ~1.0, CHARACTER test only)
#
# Cross-style comparison:
#   Sparse: Aladdin starter, Ackroyd dialogue
#   Rich: Poe, Lovecraft, Karl
#
# AI vs Human comparison:
#   AI: Sakakibara, Karl
#   Human: all others

CORPUS_SEGMENTS = {

    # ── Sparse: Victorian fairy tale ──────────────────────────────────────────

    "aladdin_cave_sparse": {
        "source": "Aladdin starter-edition",
        "author_type": "human",
        "style": "fairy_tale",
        "text": (
            "Next day the magician led Aladdin into some beautiful gardens "
            "a long way outside the city gates. They sat down by a fountain "
            "and the magician pulled a cake from his girdle, which he divided "
            "between them. Then they journeyed onwards till they almost reached "
            "the mountains."
        ),
        "scene_type": "outdoor_path",
        "expected_iei": False,
        "language_types": ["narrative", "action"],
    },

    "aladdin_lamp_sparse": {
        "source": "Aladdin starter-edition",
        "author_type": "human",
        "style": "fairy_tale",
        "text": (
            "For two days Aladdin remained in the dark, crying and lamenting. "
            "At last he clasped his hands in prayer, and in so doing rubbed the "
            "ring, which the magician had forgotten to take from him. "
            "Immediately an enormous and frightful genie rose out of the earth, "
            'saying: "What wouldst thou with me? I am the Slave of the Ring, '
            'and will obey thee in all things."'
        ),
        "scene_type": "cave_interior",
        "expected_iei": False,
        "language_types": ["narrative", "dialogue"],
    },

    # ── Rich: Gothic atmospheric (Poe) ────────────────────────────────────────

    "usher_approach_rich": {
        "source": "The Fall of the House of Usher",
        "author_type": "human",
        "style": "gothic",
        "text": (
            "During the whole of a dull, dark, and soundless day in the autumn "
            "of the year, when the clouds hung oppressively low in the heavens, "
            "I had been passing alone, on horseback, through a singularly dreary "
            "tract of country; and at length found myself, as the shades of the "
            "evening drew on, within view of the melancholy House of Usher. "
            "I know not how it was\u2014but, with the first glimpse of the building, "
            "a sense of insufferable gloom pervaded my spirit."
        ),
        "scene_type": "outdoor_approach",
        "expected_iei": False,
        "language_types": ["narrative", "introspection"],
    },

    "masque_rooms_rich": {
        "source": "The Masque of the Red Death",
        "author_type": "human",
        "style": "gothic",
        "text": (
            "The apartments were so irregularly disposed that the vision embraced "
            "but little more than one at a time. There was a sharp turn at every "
            "twenty or thirty yards, and at each turn a novel effect. "
            "That at the eastern extremity was hung, for example, in blue\u2014and "
            "vividly blue were its windows. The second chamber was purple in its "
            "ornaments and tapestries, and here the panes were purple. "
            "The third was green throughout, and so were the casements. "
            "The fourth was furnished and lighted with orange\u2014the fifth with "
            "white\u2014the sixth with violet. The seventh apartment was closely "
            "shrouded in black velvet tapestries that hung all over the ceiling "
            "and down the walls, falling in heavy folds upon a carpet of the "
            "same material."
        ),
        "scene_type": "interior_palace",
        "expected_iei": False,
        "language_types": ["descriptive"],
    },

    "cask_unreliable_narrator": {
        "source": "The Cask of Amontillado",
        "author_type": "human",
        "style": "gothic",
        "text": (
            "It was about dusk, one evening during the supreme madness of the "
            "carnival season, that I encountered my friend. He accosted me with "
            "excessive warmth, for he had been drinking much. The man wore motley. "
            "He had on a tight-fitting parti-striped dress, and his head was "
            "surmounted by the conical cap and bells. I was so pleased to see him, "
            "that I thought I should never have done wringing his hand."
        ),
        "scene_type": "outdoor_carnival",
        "expected_iei": False,
        "language_types": ["narrative", "descriptive"],
    },

    # ── Rich: Cosmic horror (Lovecraft) ───────────────────────────────────────

    "cthulhu_opening_philosophical": {
        "source": "The Call of Cthulhu",
        "author_type": "human",
        "style": "cosmic_horror",
        "text": (
            "The most merciful thing in the world, I think, is the inability of the "
            "human mind to correlate all its contents. We live on a placid island "
            "of ignorance in the midst of black seas of infinity, and it was not "
            "meant that we should voyage far. The sciences, each straining in its "
            "own direction, have hitherto harmed us little; but some day the piecing "
            "together of dissociated knowledge will open up such terrifying vistas "
            "of reality, and of our frightful position therein, that we shall either "
            "go mad from the revelation or flee from the deadly light into the peace "
            "and safety of a new dark age."
        ),
        "scene_type": "abstract_philosophical",
        "expected_iei": False,
        "language_types": ["philosophical", "narrative"],
    },

    # ── Dialogue-dominant: Detective (Christie) ───────────────────────────────

    "ackroyd_breakfast_neutral": {
        "source": "The Murder of Roger Ackroyd, Chapter I",
        "author_type": "human",
        "style": "detective",
        "text": (
            "From the dining-room on my left there came the rattle of tea-cups "
            "and the short, dry cough of my sister Caroline.\n"
            '"Is that you, James?" she called.\n'
            "An unnecessary question, since who else could it be?"
        ),
        "scene_type": "interior_domestic",
        "expected_iei": False,
        "language_types": ["dialogue", "narrative"],
    },

    # ── AI-generated: Light novel (Sakakibara) ────────────────────────────────

    "sakakibara_classroom_rich": {
        "source": "Sakakibara Kaito (AI-generated, full version)",
        "author_type": "ai",
        "style": "light_novel",
        "text": (
            "The classroom held its breath. Thirty-four students. Fifteen rows of "
            "desks arranged in that aggressively efficient grid that Japanese schools "
            "favored. The rain tapping against the windowpanes like impatient fingers. "
            "The smell of chalk dust and damp uniforms and the faint, almost "
            "imperceptible sweetness of the cherry blossoms drifting in through the "
            "open windows."
        ),
        "scene_type": "interior_classroom",
        "expected_iei": False,
        "language_types": ["descriptive"],
    },

    "sakakibara_classroom_sparse": {
        "source": "Sakakibara Kaito (AI-generated, starter version)",
        "author_type": "ai",
        "style": "light_novel",
        "text": (
            "The April rain fell in that particular way that made cherry blossom "
            "petals stick to the pavement like wet confetti. Sakakibara Kaito had "
            "been staring at the same kanji for eleven minutes\u2014not reading it, "
            "staring at it. The character was \u5f71 (kage). Shadow."
        ),
        "scene_type": "interior_classroom",
        "expected_iei": False,
        "language_types": ["narrative"],
    },

    # ── AI-generated: 2nd person extreme sensory (Karl) ───────────────────────

    "karl_classroom_sensory": {
        "source": "Karl (AI-generated, 2nd person)",
        "author_type": "ai",
        "style": "second_person_sensory",
        "text": (
            "Your chair legs scrape against the linoleum floor, a gritty, complaining "
            "sound that feels amplified in the momentary quiet. You push yourself up, "
            "your body feeling strangely heavy. The worn denim of your jeans rustles. "
            "You can feel the slightly cool, smooth surface of the window glass near "
            "your left shoulder. Outside, the morning sun casts a pale, golden light "
            "on the empty school lawn, making the dew on the grass blades glitter."
        ),
        "scene_type": "interior_classroom",
        "expected_iei": False,
        "language_types": ["descriptive", "sensory"],
    },

    "karl_hallway_social": {
        "source": "Karl (AI-generated, 2nd person)",
        "author_type": "ai",
        "style": "second_person_sensory",
        "text": (
            "The hallway is a chaotic river of bodies, a swirling mass of Champion "
            "hoodies, Lululemon leggings, and Fj\u00e4llr\u00e4ven K\u00e5nken backpacks. "
            "You step into the current, just another anonymous face in the crowd, "
            "but something feels different. You're still an unknown, but you're not "
            "a zero. You're the kid who burned his dad's roses. It's a start."
        ),
        "scene_type": "interior_hallway",
        "expected_iei": False,
        "language_types": ["narrative", "descriptive"],
    },

    "karl_panic_internal": {
        "source": "Karl (AI-generated, 2nd person)",
        "author_type": "ai",
        "style": "second_person_sensory",
        "text": (
            "Your mind goes blank. A vast, white, static-filled void where a "
            '"fun fact" should be. What happened this summer? The image of your '
            "father's face, tight and pale, flickers in your head. The crinkled "
            "edge of a DNA report on the kitchen table. The finality in his voice "
            "when he said he was cutting you off. Fun."
        ),
        "scene_type": "interior_classroom",
        "expected_iei": False,
        "language_types": ["introspection", "narrative"],
    },
}

# Backward compatibility alias
CORPUS_SELECTIONS = CORPUS_SEGMENTS

if __name__ == "__main__":
    by_style: dict[str, list[str]] = {}
    by_author: dict[str, int] = {"human": 0, "ai": 0}
    for key, seg in CORPUS_SEGMENTS.items():
        words = len(seg["text"].split())
        style = seg.get("style", "unknown")
        by_style.setdefault(style, []).append(key)
        by_author[seg["author_type"]] += 1
        print(f"{key}: {words}w | {style} | {seg['author_type']} | scene={seg['scene_type']}")

    print(f"\n--- {len(CORPUS_SEGMENTS)} segments total ---")
    print(f"Human: {by_author['human']} | AI: {by_author['ai']}")
    for style, keys in by_style.items():
        print(f"  {style}: {len(keys)} segments")
