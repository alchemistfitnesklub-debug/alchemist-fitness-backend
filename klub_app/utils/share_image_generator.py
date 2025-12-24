from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

def get_emoji_image(emoji):
    """
    Download emoji image from Twemoji CDN
    Returns PIL Image or None
    """
    # Convert emoji to unicode codepoint
    codepoint = '-'.join([hex(ord(c))[2:] for c in emoji])
    
    # Twemoji CDN URL
    url = f"https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/{codepoint}.png"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        return None
    except:
        return None

def generate_achievement_share_image(achievement_data):
    """
    Generate beautiful share image for achievement with real emoji images
    
    achievement_data = {
        'title': 'Početnik',
        'description': 'Završio 10 treninga',
        'icon': '🥉',
        'tier': 'bronze',
        'user_name': 'Lana Pavlovic',
        'progress': 10,
        'target': 10
    }
    """
    
    # Image dimensions (optimized for Instagram Stories 9:16)
    width = 1080
    height = 1920
    
    # Create image
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # Tier colors (gradient)
    tier_colors = {
        'bronze': [(255, 140, 0), (255, 165, 0)],
        'silver': [(169, 169, 169), (211, 211, 211)],
        'gold': [(255, 215, 0), (255, 223, 0)],
        'platinum': [(0, 206, 209), (64, 224, 208)]
    }
    
    tier = achievement_data.get('tier', 'bronze')
    colors = tier_colors.get(tier, tier_colors['bronze'])
    
    # Draw gradient background
    for y in range(height):
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * y / height)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * y / height)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * y / height)
        draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
    
    # Add semi-transparent overlay
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 100))
    img = img.convert('RGBA')
    img = Image.alpha_composite(img, overlay)
    img = img.convert('RGB')
    
    # Try to load fonts
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw "NOVO DOSTIGNUCE!" at top
    header_text = "NOVO POSTIGNUCE!"
    header_bbox = draw.textbbox((0, 0), header_text, font=title_font)
    header_width = header_bbox[2] - header_bbox[0]
    draw.text(((width - header_width) / 2, 200), header_text, fill=(255, 255, 255), font=title_font)
    
    # Download and paste trophy emoji at top
    trophy_emoji = get_emoji_image('🏆')
    if trophy_emoji:
        trophy_size = 100
        trophy_emoji = trophy_emoji.resize((trophy_size, trophy_size), Image.Resampling.LANCZOS)
        trophy_x = int((width - trophy_size) / 2)
        trophy_y = 80
        if trophy_emoji.mode == 'RGBA':
            img.paste(trophy_emoji, (trophy_x, trophy_y), trophy_emoji)
        else:
            img.paste(trophy_emoji, (trophy_x, trophy_y))
    
    # Download and paste achievement badge emoji - LARGE
    icon = achievement_data.get('icon', '🏆')
    badge_emoji = get_emoji_image(icon)
    if badge_emoji:
        badge_size = 400  # Large emoji
        badge_emoji = badge_emoji.resize((badge_size, badge_size), Image.Resampling.LANCZOS)
        badge_x = int((width - badge_size) / 2)
        badge_y = 400
        
        # Draw white circle background
        circle_padding = 50
        circle_x = badge_x - circle_padding
        circle_y = badge_y - circle_padding
        circle_size = badge_size + (circle_padding * 2)
        draw.ellipse(
            [(circle_x, circle_y), (circle_x + circle_size, circle_y + circle_size)],
            fill=(255, 255, 255, 30)
        )
        
        # Paste emoji
        if badge_emoji.mode == 'RGBA':
            img.paste(badge_emoji, (badge_x, badge_y), badge_emoji)
        else:
            img.paste(badge_emoji, (badge_x, badge_y))
    else:
        # Fallback: Draw tier text if emoji download fails
        tier_text = tier.upper()
        tier_bbox = draw.textbbox((0, 0), tier_text, font=subtitle_font)
        tier_width = tier_bbox[2] - tier_bbox[0]
        draw.text(((width - tier_width) / 2, 500), tier_text, fill=(255, 255, 255), font=subtitle_font)
    
    # Draw achievement title
    title = achievement_data.get('title', 'Achievement')
    title_bbox = draw.textbbox((0, 0), title, font=subtitle_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) / 2, 880), title, fill=(255, 255, 255), font=subtitle_font)
    
    # Draw description
    description = achievement_data.get('description', '')
    desc_bbox = draw.textbbox((0, 0), description, font=text_font)
    desc_width = desc_bbox[2] - desc_bbox[0]
    draw.text(((width - desc_width) / 2, 1000), description, fill=(255, 255, 255), font=text_font)
    
    # Draw progress bar
    progress = achievement_data.get('progress', 0)
    target = achievement_data.get('target', 100)
    progress_percentage = min(progress / target * 100, 100) if target > 0 else 100
    
    bar_width = 800
    bar_height = 40
    bar_x = (width - bar_width) / 2
    bar_y = 1130
    
    # Background bar (dark)
    draw.rounded_rectangle(
        [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
        radius=20,
        fill=(50, 50, 50)
    )
    
    # Progress bar (white)
    progress_width = int(bar_width * progress_percentage / 100)
    if progress_width > 0:
        draw.rounded_rectangle(
            [(bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height)],
            radius=20,
            fill=(255, 255, 255)
        )
    
    # Progress text
    progress_text = f"{progress}/{target}"
    progress_bbox = draw.textbbox((0, 0), progress_text, font=text_font)
    progress_text_width = progress_bbox[2] - progress_bbox[0]
    draw.text(((width - progress_text_width) / 2, bar_y + 60), progress_text, fill=(255, 255, 255), font=text_font)
    
    # Draw user name
    user_name = achievement_data.get('user_name', 'User')
    name_bbox = draw.textbbox((0, 0), user_name, font=text_font)
    name_width = name_bbox[2] - name_bbox[0]
    draw.text(((width - name_width) / 2, 1280), user_name, fill=(255, 255, 255), font=text_font)
    
    # Draw Alchemist branding at bottom
    brand_text = "ALCHEMIST HEALTH CLUB"
    brand_bbox = draw.textbbox((0, 0), brand_text, font=text_font)
    brand_width = brand_bbox[2] - brand_bbox[0]
    brand_y = 1600
    
    # Download and paste muscle emoji
    muscle_emoji = get_emoji_image('💪')
    if muscle_emoji:
        muscle_size = 60
        muscle_emoji = muscle_emoji.resize((muscle_size, muscle_size), Image.Resampling.LANCZOS)
        muscle_x = int((width - brand_width) / 2 - muscle_size - 20)
        muscle_y = brand_y - 10
        if muscle_emoji.mode == 'RGBA':
            img.paste(muscle_emoji, (muscle_x, muscle_y), muscle_emoji)
        else:
            img.paste(muscle_emoji, (muscle_x, muscle_y))
    
    draw.text(((width - brand_width) / 2, brand_y), brand_text, fill=(255, 255, 255), font=text_font)
    
    instagram_text = "@alchemist.bgd"
    insta_bbox = draw.textbbox((0, 0), instagram_text, font=small_font)
    insta_width = insta_bbox[2] - insta_bbox[0]
    draw.text(((width - insta_width) / 2, 1720), instagram_text, fill=(255, 255, 255), font=small_font)
    
    # Save to BytesIO
    img_io = BytesIO()
    img.save(img_io, format='PNG', quality=95)
    img_io.seek(0)
    
    return img_io
