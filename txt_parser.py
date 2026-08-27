import re

def parse_txt_questions(file_content: str) -> list:
    """
    Parses questions from raw text content.
    Supports formats:
    
    Q: What is the capital of India?
    A) Mumbai
    B) New Delhi ✅
    C) Kolkata
    D) Chennai
    Exp: New Delhi is capital of India
    ---
    """
    questions = []
    blocks = re.split(r'\n\s*---\s*\n|\n\s*===\s*\n', file_content)
    current_section = "General"

    for block in blocks:
        lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
        if not lines:
            continue

        # Check section header
        sec_match = re.match(r'\[\s*(?:Section|Subject):\s*(.+?)\s*\]', lines[0], re.IGNORECASE)
        if sec_match:
            current_section = sec_match.group(1)
            lines = lines[1:]
            if not lines:
                continue

        q_text = ""
        options = []
        correct_idx = None
        explanation = ""

        for line in lines:
            if re.match(r'^(?:Q|Question)\s*\d*[:.]', line, re.IGNORECASE):
                q_text = re.sub(r'^(?:Q|Question)\s*\d*[:.]', '', line, flags=re.IGNORECASE).strip()
            elif re.match(r'^(?:Ans|Answer|Correct)\s*[:.]', line, re.IGNORECASE):
                ans_str = re.sub(r'^(?:Ans|Answer|Correct)\s*[:.]', '', line, flags=re.IGNORECASE).strip()
                if ans_str.isdigit():
                    correct_idx = int(ans_str) - 1
                elif len(ans_str) == 1 and ans_str.upper() in "ABCD":
                    correct_idx = "ABCD".index(ans_str.upper())
            elif re.match(r'^(?:Exp|Explanation)\s*[:.]', line, re.IGNORECASE):
                explanation = re.sub(r'^(?:Exp|Explanation)\s*[:.]', '', line, flags=re.IGNORECASE).strip()
            else:
                # Check option line A), B) or 1., 2.
                opt_match = re.match(r'^(?:[A-D1-4]\s*[\.\)-]|\([A-D1-4]\))\s*(.+)', line, re.IGNORECASE)
                if opt_match:
                    opt_val = opt_match.group(1).strip()
                    if "✅" in opt_val or "[correct]" in opt_val.lower():
                        correct_idx = len(options)
                        opt_val = opt_val.replace("✅", "").replace("[correct]", "").replace("[CORRECT]", "").strip()
                    options.append(opt_val)
                elif not q_text:
                    q_text = line

        if q_text and len(options) >= 2:
            if correct_idx is None or correct_idx >= len(options):
                correct_idx = 0  # Default fallback to first option
            questions.append({
                "section_name": current_section,
                "question_text": q_text,
                "options": options,
                "correct_option": correct_idx,
                "explanation": explanation
            })

    return questions
