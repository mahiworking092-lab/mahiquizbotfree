import re

def parse_txt_questions(file_content: str) -> list:
    """
    Parses quiz questions from raw text content.
    Supports single or multiple questions formatted in various styles:
    - Advance Quiz Bot exports
    - Double-newline separated blocks (\n\n)
    - Dashed line separated blocks (---, ===, ***)
    - Standard numbered formats (1., Q1., Q:)
    - Answers marked with ✅, [correct], or Ans: B / Answer: 2
    - Optional explanations starting with Exp: or Explanation:
    - Section headers [Section: Math]
    """
    if not file_content or not file_content.strip():
        return []

    # Clean Windows line endings
    content = file_content.replace('\r\n', '\n').replace('\r', '\n')

    # Remove noise like metadata lines RT: or ID:
    content = re.sub(r'^(?:RT|ID):\s*.*$', '', content, flags=re.MULTILINE | re.IGNORECASE)

    # Determine splitting strategy
    blocks = []
    if re.search(r'\n\s*(?:---|===|\*\*\*)+\s*\n', content):
        blocks = re.split(r'\n\s*(?:---|===|\*\*\*)+\s*\n', content)
    else:
        # Split by double/multiple blank lines
        raw_blocks = re.split(r'\n\s*\n+', content)
        for b in raw_blocks:
            if b.strip():
                # Check if a single block accidentally contains multiple numbered questions e.g. "1. ... \n 2. ..."
                sub_blocks = re.split(r'\n(?=(?:Q|Question|\d+)\s*[\.:\)])', b, flags=re.IGNORECASE)
                blocks.extend([sb for sb in sub_blocks if sb.strip()])

    questions = []
    current_section = "General"

    # Option regex pattern matching A), A., (A), 1), 1., (1), a), a.
    opt_pattern = re.compile(
        r'^(?:[A-Da-d1-4][\.\)\-]|[\(][A-Da-d1-4][\)])\s*(.+)',
        re.IGNORECASE
    )

    for block in blocks:
        lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
        if not lines:
            continue

        # Check section header
        sec_match = re.match(r'\[\s*(?:Section|Subject):\s*(.+?)\s*\]', lines[0], re.IGNORECASE)
        if sec_match:
            current_section = sec_match.group(1).strip()
            lines = lines[1:]
            if not lines:
                continue

        q_lines = []
        options = []
        correct_idx = None
        ans_letter_or_num = None
        explanation = ""

        for line in lines:
            # Check Explanation
            exp_match = re.match(r'^(?:Exp|Explanation|Ex|Note)\s*[:.]\s*(.+)', line, re.IGNORECASE)
            if exp_match:
                explanation = exp_match.group(1).strip()
                continue

            # Check Answer line e.g., "Ans: B", "Answer: 2", "Correct: A"
            ans_match = re.match(r'^(?:Ans|Answer|Correct)\s*[:.]\s*(.+)', line, re.IGNORECASE)
            if ans_match:
                ans_str = ans_match.group(1).strip()
                if ans_str.isdigit():
                    ans_letter_or_num = int(ans_str) - 1
                elif len(ans_str) >= 1 and ans_str[0].upper() in "ABCD":
                    ans_letter_or_num = "ABCD".index(ans_str[0].upper())
                continue

            # Check Option line
            opt_match = opt_pattern.match(line)
            if opt_match:
                opt_val = opt_match.group(1).strip()
                # Check for correct answer marker inside option
                if "✅" in opt_val or "[correct]" in opt_val.lower() or "(correct)" in opt_val.lower():
                    correct_idx = len(options)
                    opt_val = re.sub(r'✅|\[correct\]|\(correct\)', '', opt_val, flags=re.IGNORECASE).strip()
                options.append(opt_val)
            elif "✅" in line or "[correct]" in line.lower() or "(correct)" in line.lower():
                correct_idx = len(options)
                opt_val = re.sub(r'✅|\[correct\]|\(correct\)', '', line, flags=re.IGNORECASE).strip()
                options.append(opt_val)
            else:
                # If options haven't started, treat as question text line
                if not options:
                    clean_line = line
                    if not q_lines:  # Only for first line of question
                        clean_line = re.sub(
                            r'^(?:Q|Question)?\s*\d*\s*[\.:\)]\s*',
                            '',
                            line,
                            flags=re.IGNORECASE
                        ).strip()
                        clean_line = re.sub(r'\[\s*Q?\s*\d+/\d+\s*\]', '', clean_line, flags=re.IGNORECASE).strip()
                    if clean_line:
                        q_lines.append(clean_line)

        q_text = "\n".join(q_lines).strip()

        # If answer line specified correct index
        if correct_idx is None and ans_letter_or_num is not None:
            correct_idx = ans_letter_or_num

        if q_text and len(options) >= 2:
            if correct_idx is None or correct_idx >= len(options) or correct_idx < 0:
                correct_idx = 0  # Fallback to 1st option if not marked
            
            questions.append({
                "section_name": current_section,
                "question_text": q_text,
                "options": options,
                "correct_option": correct_idx,
                "explanation": explanation
            })

    return questions
