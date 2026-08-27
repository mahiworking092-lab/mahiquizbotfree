import io
from PIL import Image, ImageDraw, ImageFont

def generate_leaderboard_image(quiz_title: str, leaderboard_data: list, total_questions: int) -> io.BytesIO:
    width, height = 900, max(600, 200 + len(leaderboard_data) * 55)
    
    # Create dark gradient background
    img = Image.new("RGB", (width, height), color=(20, 24, 38))
    draw = ImageDraw.Draw(img)

    # Use default PIL font (fallback safe across platforms)
    try:
        title_font = ImageFont.truetype("arial.ttf", 32)
        header_font = ImageFont.truetype("arial.ttf", 22)
        row_font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        row_font = ImageFont.load_default()

    # Draw Header Box
    draw.rectangle([0, 0, width, 120], fill=(30, 36, 56))
    draw.text((30, 25), "🏆 QUIZ LEADERBOARD 🏆", fill=(255, 215, 0), font=title_font)
    draw.text((30, 70), f"Quiz: {quiz_title} | Total Questions: {total_questions}", fill=(200, 210, 230), font=header_font)

    # Table Column X-Coordinates
    col_rank = 40
    col_name = 150
    col_correct = 520
    col_wrong = 680
    col_score = 800

    # Draw Table Header
    y_start = 140
    draw.rectangle([20, y_start, width - 20, y_start + 40], fill=(45, 53, 80))
    draw.text((col_rank, y_start + 8), "RANK", fill=(255, 255, 255), font=header_font)
    draw.text((col_name, y_start + 8), "NAME", fill=(255, 255, 255), font=header_font)
    draw.text((col_correct, y_start + 8), "CORRECT", fill=(100, 255, 100), font=header_font)
    draw.text((col_wrong, y_start + 8), "WRONG", fill=(255, 100, 100), font=header_font)
    draw.text((col_score, y_start + 8), "SCORE", fill=(255, 215, 0), font=header_font)

    # Medals / Badges
    medals = {1: "1st [GOLD]", 2: "2nd [SILVER]", 3: "3rd [BRONZE]"}

    # Draw Table Rows
    curr_y = y_start + 50
    for idx, user in enumerate(leaderboard_data[:15], start=1):
        row_bg = (35, 42, 66) if idx % 2 == 0 else (28, 34, 52)
        draw.rectangle([20, curr_y, width - 20, curr_y + 45], fill=row_bg)

        rank_str = medals.get(idx, f"#{idx}")
        name = user.get('user_name', 'User')
        if len(name) > 25:
            name = name[:22] + "..."
        correct = user.get('correct_count', 0)
        wrong = user.get('wrong_count', 0)
        total_ans = correct + wrong
        score_pct = int((correct / total_questions * 100)) if total_questions > 0 else 0

        # Colors for top ranks
        rank_color = (255, 215, 0) if idx == 1 else (192, 192, 192) if idx == 2 else (205, 127, 50) if idx == 3 else (255, 255, 255)

        draw.text((col_rank, curr_y + 12), rank_str, fill=rank_color, font=row_font)
        draw.text((col_name, curr_y + 12), name, fill=(255, 255, 255), font=row_font)
        draw.text((col_correct, curr_y + 12), f"{correct}", fill=(120, 255, 120), font=row_font)
        draw.text((col_wrong, curr_y + 12), f"{wrong}", fill=(255, 120, 120), font=row_font)
        draw.text((col_score, curr_y + 12), f"{score_pct}%", fill=(255, 215, 0), font=row_font)

        curr_y += 50

    # Save to IO Bytes Buffer
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
