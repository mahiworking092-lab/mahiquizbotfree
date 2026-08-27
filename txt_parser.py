import re
import json

def parse_txt_questions(file_content: str) -> list:
    """
    Parses quiz questions from raw text content or JSON formatted text files.
    Supports:
    - Advance Quiz Bot exports (.txt and .json in .txt)
    - Double-newline separated blocks (\n\n)
    - Dashed line separated blocks (---, ===, ***)
    - Standard numbered formats (1., Q1., Q:)
    - Answers marked with ✅, ✔, [correct], or Ans: B / Answer: 2
    - Optional explanations starting with Exp: or Explanation: or Ex:
    - Section headers [Section: Math]
    """
    if not file_content or not file_content.strip():
        return []

    # Strip UTF-8 BOM if present
    content = file_content.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n').strip()

    # 1. Fallback: Try JSON parsing if content looks like JSON
    if content.startswith('{') or content.startswith('['):
        try:
            data = json.loads(content)
            raw_qs = []
            if isinstance(data, dict):
                raw_qs = data.get('questions', data.get('quiz', []))
                if isinstance(raw_qs, dict):
                    raw_qs = raw_qs.get('questions', [])
            elif isinstance(data, list):
                raw_qs = data

            json_questions = []
            for item in raw_qs:
                if not isinstance(item, dict):
                    continue
                q_text = item.get('question_text') or item.get('question') or item.get('title') or ""
                opts_raw = item.get('options') or []
                
                options = []
                correct_idx = item.get('correct_option', item.get('correct_option_id', 0))
                
                if isinstance(opts_raw, list):
                    for idx, opt in enumerate(opts_raw):
                        if isinstance(opt, dict):
                            opt_txt = opt.get('text') or opt.get('option') or str(opt)
                            if opt.get('is_correct') or opt.get('correct'):
                                correct_idx = len(options)
                            options.append(str(opt_txt).strip())
                        elif isinstance(opt, str):
                            if "✅" in opt or "✔" in opt:
                                correct_idx = len(options)
                                opt = re.sub(r'✅|✔', '', opt).strip()
                            options.append(opt.strip())

                exp = item.get('explanation') or item.get('exp') or ""
                sec = item.get('section_name') or item.get('section') or "General"

                if q_text and len(options) >= 2:
                    if not isinstance(correct_idx, int) or correct_idx >= len(options) or correct_idx < 0:
                        correct_idx = 0
                    json_questions.append({
                        "section_name": sec,
                        "question_text": str(q_text).strip(),
                        "options": options,
                        "correct_option": correct_idx,
                        "explanation": str(exp).strip()
                    })

            if json_questions:
                return json_questions
        except Exception:
            pass  # Not valid JSON, proceed to text parsing

    # 2. Text Parsing Engine
    # Clean out bot metadata tags like <ggn>...</ggn>, RT:, ID:
    content = re.sub(r'<ggn>.*?</ggn>', '', content, flags=re.DOTALL)

    # Determine block splitting strategy
    if re.search(r'\n\s*(?:---|===|\*\*\*)+\s*\n', content):
        blocks = re.split(r'\n\s*(?:---|===|\*\*\*)+\s*\n', content)
    else:
        blocks = re.split(r'\n\s*\n+', content)

    questions = []
    current_section = "General"
    opt_re = re.compile(r'^\s*(?:[A-Da-d1-4][\.\)\-]|[\(][A-Da-d1-4][\)])\s*(.+)')

    for block in blocks:
        block_str = block.strip()
        if not block_str:
            continue

        # Ignore standalone section header block [Section: XYZ]
        sec_match = re.match(r'^\[\s*(?:Section|Subject):\s*(.+?)\s*\]$', block_str, re.IGNORECASE)
        if sec_match:
            current_section = sec_match.group(1).strip()
            continue

        lines = block_str.split('\n')

        # Check section header on first line of block
        if lines and re.match(r'^\[\s*(?:Section|Subject):\s*(.+?)\s*\]$', lines[0].strip(), re.IGNORECASE):
            current_section = re.match(r'^\[\s*(?:Section|Subject):\s*(.+?)\s*\]$', lines[0].strip(), re.IGNORECASE).group(1).strip()
            lines = lines[1:]

        filtered_lines = []
        explanation = ""
        ans_letter_or_num = None

        for ln in lines:
            s_ln = ln.strip()
            if not s_ln or s_ln.startswith(("RT:", "ID:")):
                continue

            # Check Explanation line
            if re.match(r'^(?:Ex|Exp|Explanation|Note)\s*[:.]', s_ln, re.IGNORECASE):
                explanation = re.sub(r'^(?:Ex|Exp|Explanation|Note)\s*[:.]\s*', '', s_ln, flags=re.IGNORECASE).strip()
                continue

            # Check explicit Answer line e.g., Ans: B, Answer: 2
            ans_match = re.match(r'^(?:Ans|Answer|Correct)\s*[:.]\s*(.+)', s_ln, re.IGNORECASE)
            if ans_match:
                ans_str = ans_match.group(1).strip()
                if ans_str.isdigit():
                    ans_letter_or_num = int(ans_str) - 1
                elif len(ans_str) >= 1 and ans_str[0].upper() in "ABCD":
                    ans_letter_or_num = "ABCD".index(ans_str[0].upper())
                continue

            filtered_lines.append(ln)

        if not filtered_lines:
            continue

        # Locate where options start in the block
        opt_start_idx = None
        for idx, ln in enumerate(filtered_lines):
            s_ln = ln.strip()
            if not s_ln:
                continue
            # Check emoji or dashed separator line between question and options (e.g. ⚡⚡⚡⚡ or ---)
            if re.match(r'^[^\w\s]{3,}$', s_ln) and not any(c in s_ln for c in '✅✔'):
                opt_start_idx = idx + 1
                break
            if opt_re.match(s_ln):
                opt_start_idx = idx
                break

        if opt_start_idx is None:
            # Fallback: line 0 is question, remaining lines are options
            opt_start_idx = 1 if len(filtered_lines) > 1 else 0

        q_lines = filtered_lines[:opt_start_idx]
        opt_lines = filtered_lines[opt_start_idx:]

        # Clean question text
        q_text_raw = "\n".join([l.strip() for l in q_lines if l.strip()])
        # Strip leading question number/prefix (e.g. "1. ", "Q1: ", "Question 1: ", "quiz_GGN7QD4TH.txt")
        q_text = re.sub(r'^(?:Q|Question)?\s*\d*\s*[\.:\)]\s*', '', q_text_raw, flags=re.IGNORECASE).strip()
        q_text = re.sub(r'\[\s*Q?\s*\d+/\d+\s*\]', '', q_text, flags=re.IGNORECASE).strip()
        # Remove filename header if first line was a filename e.g. "quiz_xxxx.txt"
        q_text = re.sub(r'^[a-zA-Z0-9_\-]+\.txt\s*\n?', '', q_text, flags=re.IGNORECASE).strip()

        if not q_text and q_text_raw:
            q_text = q_text_raw

        options = []
        correct_idx = None

        for ln in opt_lines:
            s_ln = ln.strip()
            if not s_ln:
                continue
            
            # Strip option prefix like A), A., (A), 1), 1., (1)
            opt_val = re.sub(r'^\s*(?:[A-Da-d1-4][\.\)\-]|[\(][A-Da-d1-4][\)])\s*', '', s_ln)
            
            # Check for correct answer mark: ✅, ✔, [correct], (correct)
            if any(m in opt_val for m in ['✅', '✔', '[correct]', '[CORRECT]', '(correct)', '(CORRECT)']):
                correct_idx = len(options)
                opt_val = re.sub(r'✅|✔|\[correct\]|\(correct\)', '', opt_val, flags=re.IGNORECASE).strip()
            
            options.append(opt_val)

        if correct_idx is None and ans_letter_or_num is not None:
            correct_idx = ans_letter_or_num

        if q_text and len(options) >= 2:
            if correct_idx is None or correct_idx >= len(options) or correct_idx < 0:
                correct_idx = 0  # Default fallback to 1st option if not explicitly marked
            
            questions.append({
                "section_name": current_section,
                "question_text": q_text,
                "options": options,
                "correct_option": correct_idx,
                "explanation": explanation
            })

    return questions
