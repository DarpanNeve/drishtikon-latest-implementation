# core/text_utils.py
# ================================================================
#  TEXT UTILITIES
#  - Sentence splitting with forgiving behavior for OCR'd text
# ================================================================

import re
from typing import List


def split_into_sentences(text: str, min_len: int = 10, max_len: int = 100) -> List[str]:
    """
    Split text into 'forgiving' sentence chunks.

    Forgiving behavior:
    - Split on ., ?, ! followed by whitespace
    - Strip whitespace around each piece
    - Drop completely empty chunks
    - Merge very short fragments (len < min_len) into the previous sentence
      to reduce OCR-induced fragmentation.

    This is designed for noisy OCR text where:
    - Abbreviations (e.g., "Dr.", "Mr.") may appear
    - Line breaks or hyphenation may cause tiny fragments
    """
    if not text:
        return []

    # Basic split on sentence-ending punctuation + whitespace
    raw_chunks = re.split(r'(?<=[.!?;])', text)

    # Clean up whitespace and remove empties
    cleaned = [chunk.strip() for chunk in raw_chunks if chunk and chunk.strip()]
    if not cleaned:
        return []

    sentences: List[str] = []
    for chunk in cleaned:
        if sentences and len(chunk) < min_len and len(chunk) + len(sentences[-1]) < max_len:
            sentences[-1] = sentences[-1] + " " + chunk
        elif len(chunk) > max_len and sentences:
            chunk_words = chunk.split(" ")
            mid = len(chunk_words) // 2
            if mid == 0:
                final_sentences.append(chunk)
                continue
            first_half, second_half = " ".join(chunk_words[:mid]), " ".join(chunk_words[mid:])
            sentences.extend([first_half, second_half])
        else:
            sentences.append(chunk)


    return sentences


if __name__ == "__main__":
    # Test case from previous interaction:
    sample = (
        '''    
CHAPTER FOUR

A Magical Meeting with
the Sages of Sivana

After walking for many hours along an intricate series of paths and grassy trails, the two travellers came upon a lush, green valley. On one side of the valley, the snow-capped Himalayas offered their protection, like weather-beaten soldiers guarding the place where their generals rested. On the other, a thick forest of pine trees sprouted, a perfectly natural tribute to this enchanting fantasyland.

The sage looked at Julian and smiled gently. "Welcome to the Nirvana of Sivana."

The two then descended along another less-travelled way and into the thick forest that formed the floor of the valley. The smell of pine and sandalwood wafted through the cool, crisp mountain air. Julian, now barefoot to ease his aching feet, felt the damp moss under his toes. He was surprised to see richly colored orchids and lovely flowers dancing among the trees, as if rejoicing in the beauty and splendor of this tiny slice of Heaven. In the distance, Julian could hear gentle voices, soft and soothing to the ear. He continued to follow the sage without making a sound. After walking for about fifteen more minutes, the

24

The Monk Who Said His Ferrari

two men reached a clearing. Before him was a sight that even the worldly wise and rarely surprised Julian Mantle could never have imagined — a small village made solely out of what appeared to be roses. At the center of the village was a tiny temple, the kind Julian had seen on his trips to Thailand and Nepal, but this temple was made of red, white and pink flowers, held together with long strands of multi-colored string and twigs. The little huts that dotted the remaining space appeared to be the austere homes of the sages. These were also made of roses. Julian was speechless. As for the monks who inhabited the village, those he could see looked like Julian's travelling companion, who now revealed that his name was Yogi Raman and the leader of this group. The citizens of this dreamlike colony looked astonishingly youthful and moved with poise and purpose. None of them spoke, choosing instead to respect the tranquillity of this place by performing their tasks in silence.

The men, who appeared to number only about ten, wore the same red-robed uniform as Yogi Raman and smiled serenely at Julian as he entered their village. Each of them looked calm, healthy and deeply contented. It was as if the tensions that plague so many of us in our modern world had sensed that they were not welcome at this summit of serenity and moved on to more inviting prospects. Though it had been many years since there had been a new face among them, these men were controlled in their reception, offering a simple bow as their greeting to this visitor who had travelled so far to find them.

The women were equally impressive. In their flowing pink silk saris and with white lotuses adorning their jet black hair, they moved busily through the village with exceptional agility.

25'''
    )
    
    print("--- Testing split_into_sentences (Simplified Final Version) ---")
    
    sentences = split_into_sentences(sample, min_len=10, max_len=100)
    for i, s in enumerate(sentences, 1):
        print(f"({len(s)} chars) {i}: {s}")
