
import re
import sys
import os
import json
import html
import urllib.parse
from weasyprint import HTML

def parse_deck_to_html(html_content):
    # Try to extract embedded config JSON from deckBuilderMount (if present)
    config_mapping = {}
    config_match = re.search(r'<div[^>]+id="deckBuilderMount"[^>]+config="(.*?)"', html_content, re.DOTALL)
    if config_match:
        raw_config = config_match.group(1)
        try:
            # HTML attribute is escaped (e.g. &quot;), decode then load JSON
            decoded = html.unescape(raw_config)
            cfg = json.loads(decoded)
            # cfg may contain a 'cards' array or similar. Build name->(id,slug) map.
            if isinstance(cfg, dict):
                # normalize possible card lists
                card_lists = []
                if 'cards' in cfg and isinstance(cfg['cards'], list):
                    card_lists.append(cfg['cards'])
                if 'allCards' in cfg and isinstance(cfg['allCards'], list):
                    card_lists.append(cfg['allCards'])
                # Some snapshots include 'cards' nested under other keys; flatten common places
                for lst in card_lists:
                    for c in lst:
                        # try to get localized name fields
                        name = None
                        if isinstance(c, dict):
                            # prefer Japanese name fields if present
                            name = c.get('name') or c.get('localizedName') or c.get('displayName')
                            cid = c.get('id') or c.get('cardId') or c.get('cardID')
                            slug = c.get('slug') or c.get('canonicalSlug')
                            if name and cid and slug:
                                config_mapping[name] = (cid, slug)
        except Exception:
            # graceful fallback: leave config_mapping empty
            config_mapping = {}

    card_rows = re.findall(r'<div class="CardRow__CardRowStyles-sc-1jw5czv-0.*?</div></div>', html_content, re.DOTALL)

    # If the user provided a list of per-image links, use them in order for the image anchors.
    # This list was provided externally; keep it here so image hrefs match the desired sequence.
    image_links = [
        "https://hearthstone.blizzard.com/ja-jp/cards/102983-zilliax-deluxe-000?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%B8%E3%83%AA%E3%82%A2%E3%83%83%E3%82%AF%E3%82%B9DX3000",
        "https://hearthstone.blizzard.com/ja-jp/cards/59223-raise-dead?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E6%AD%BB%E8%80%85%E8%98%87%E7%94%9F",
        "https://hearthstone.blizzard.com/ja-jp/cards/103664-guldans-gift?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%B0%E3%83%AB%E3%83%80%E3%83%B3%E3%81%AE%E8%B4%88%E3%82%8A%E7%89%A9",
        "https://hearthstone.blizzard.com/ja-jp/cards/71781-sir-finley-sea-guide?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E6%B5%B7%E3%81%AE%E6%A1%88%E5%86%85%E4%BA%BA%E3%82%B5%E3%83%BC%E3%83%BB%E3%83%95%E3%82%A3%E3%83%B3%E3%83%AC%E3%83%BC",
        "https://hearthstone.blizzard.com/ja-jp/cards/86626-astalor-bloodsworn?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%A2%E3%82%B9%E3%82%BF%E3%83%A9%E3%83%BC%E3%83%BB%E3%83%96%E3%83%A9%E3%83%83%E3%83%89%E3%82%B9%E3%82%A6%E3%82%A9%E3%83%BC%E3%83%B3",
        "https://hearthstone.blizzard.com/ja-jp/cards/91078-audio-amplifier?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%AA%E3%83%BC%E3%83%87%E3%82%A3%E3%82%AA%E3%83%BB%E3%82%A2%E3%83%B3%E3%83%97",
        "https://hearthstone.blizzard.com/ja-jp/cards/52698-plot-twist?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%81%A9%E3%82%93%E3%81%A7%E3%82%93%E8%BF%94%E3%81%97",
        "https://hearthstone.blizzard.com/ja-jp/cards/53756-zephrys-the-great?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E5%81%89%E5%A4%A7%E3%81%AA%E3%82%8B%E3%82%BC%E3%83%95%E3%83%AA%E3%82%B9",
        "https://hearthstone.blizzard.com/ja-jp/cards/138-doomsayer?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E7%B5%82%E6%9C%AB%E4%BA%88%E8%A8%80%E8%80%85",
        "https://hearthstone.blizzard.com/ja-jp/cards/41871-corrupting-mist?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E5%B4%A9%E5%A3%8A%E3%81%AE%E9%9C%A7",
        "https://hearthstone.blizzard.com/ja-jp/cards/46403-zola-the-gorgon?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%B4%E3%83%AB%E3%82%B4%E3%83%B3%E3%83%BB%E3%82%BE%E3%83%BC%E3%83%A9",
        "https://hearthstone.blizzard.com/ja-jp/cards/41243-stonehill-defender?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%B9%E3%83%88%E3%83%BC%E3%83%B3%E3%83%92%E3%83%AB%E3%81%AE%E5%AE%88%E8%AD%B7%E8%80%85",
        "https://hearthstone.blizzard.com/ja-jp/cards/2949-brann-bronzebeard?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%96%E3%83%A9%E3%83%B3%E3%83%BB%E3%83%96%E3%83%AD%E3%83%B3%E3%82%BA%E3%83%93%E3%82%A2%E3%83%BC%E3%83%89",
        "https://hearthstone.blizzard.com/ja-jp/cards/79767-prince-renathal?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%AC%E3%83%8A%E3%82%B5%E3%83%AB%E5%A4%AA%E5%AD%90",
        "https://hearthstone.blizzard.com/ja-jp/cards/70107-full-blown-evil?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E6%82%AA%E3%81%AE%E5%A4%A7%E8%BC%AA",
        "https://hearthstone.blizzard.com/ja-jp/cards/54891-dark-skies?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E7%A9%BA%E3%82%92%E8%A6%86%E3%81%86%E6%9A%97%E9%BB%92",
        "https://hearthstone.blizzard.com/ja-jp/cards/950-hellfire?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E5%9C%B0%E7%8D%84%E3%81%AE%E7%82%8E",
        "https://hearthstone.blizzard.com/ja-jp/cards/41247-vicious-fledgling?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E7%8D%B0%E7%8C%9B%E3%81%AA%E3%83%92%E3%83%8A",
        "https://hearthstone.blizzard.com/ja-jp/cards/40408-kazakus?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%AB%E3%82%B6%E3%82%AB%E3%82%B9",
        "https://hearthstone.blizzard.com/ja-jp/cards/102170-gaslight-gatekeeper?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%AC%E3%82%B9%E7%87%88%E3%81%AE%E3%82%AC%E3%82%B9%E3%83%88",
        "https://hearthstone.blizzard.com/ja-jp/cards/56511-the-dark-portal?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%80%E3%83%BC%E3%82%AF%E3%83%9D%E3%83%BC%E3%82%BF%E3%83%AB",
        "https://hearthstone.blizzard.com/ja-jp/cards/108967-griftah-trusted-vendor?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E6%AD%A3%E7%9B%B4%E5%95%86%E4%BA%BA%E3%82%B0%E3%83%AA%E3%83%95%E3%82%BF%E3%83%BC",
        "https://hearthstone.blizzard.com/ja-jp/cards/64894-dark-alley-pact?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E8%A3%8F%E9%80%9A%E3%82%8A%E3%81%AE%E5%8F%96%E6%B1%BA%E3%82%81",
        "https://hearthstone.blizzard.com/ja-jp/cards/55432-kobold-stickyfinger?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%B3%E3%83%9C%E3%83%AB%E3%83%88%E3%81%AE%E6%A3%92%E3%83%89%E3%83%AD",
        "https://hearthstone.blizzard.com/ja-jp/cards/78079-steamcleaner?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%B9%E3%83%81%E3%83%BC%E3%83%A0",
        "https://hearthstone.blizzard.com/ja-jp/cards/2262-emperor-thaurissan?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%BD%E3%83%BC%E3%83%AA%E3%82%B5%E3%83%B3%E7%9A%87%E5%B8%9D",
        "https://hearthstone.blizzard.com/ja-jp/cards/55419-platebreaker?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%97%E3%83%AC%E3%83%BC%E3%83%88%E3%83%96%E3%83%AC%E3%82%A4%E3%82%AB%E3%83%BC",
        "https://hearthstone.blizzard.com/ja-jp/cards/91001-symphony-of-sins?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E4%BA%A4%E9%9F%BF%E6%9B%B2%E7%AC%AC6%E7%95%AA%E3%80%8C%E5%A4%A7%E7%BD%AA%E3%80%8D",
        "https://hearthstone.blizzard.com/ja-jp/cards/2037-antique-healbot?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E9%AA%A8%E8%91%A3%E5%93%81%E3%81%AE%E3%83%92%E3%83%BC%E3%83%AB%E3%83%AD%E3%83%9C",
        "https://hearthstone.blizzard.com/ja-jp/cards/117723-bob-the-bartender?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%90%E3%83%BC%E3%83%86%E3%83%B3%E3%83%80%E3%83%BC%E3%81%AE%E3%83%9C%E3%83%96",
        "https://hearthstone.blizzard.com/ja-jp/cards/64711-battleground-battlemaster?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%90%E3%83%88%E3%83%AB%E3%82%B0%E3%83%A9%E3%82%A6%E3%83%B3%E3%83%89%E3%81%AE%E3%83%90%E3%83%88%E3%83%AB%E3%83%9E%E3%82%B9%E3%82%BF%E3%83%BC",
        "https://hearthstone.blizzard.com/ja-jp/cards/2883-reno-jackson?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%AC%E3%83%8E%E3%83%BB%E3%82%B8%E3%83%A3%E3%82%AF%E3%82%BD%E3%83%B3",
        "https://hearthstone.blizzard.com/ja-jp/cards/76984-theotar-the-mad-duke?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E7%8B%82%E4%B9%B1%E5%85%AC%E7%88%B5%E3%82%B7%E3%82%AA%E3%82%BF%E3%83%BC",
        "https://hearthstone.blizzard.com/ja-jp/cards/61640-silas-darkmoon?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%B5%E3%82%A4%E3%83%A9%E3%82%B9%E3%83%BB%E3%83%80%E3%83%BC%E3%82%AF%E3%83%A0%E3%83%BC%E3%83%B3",
        "https://hearthstone.blizzard.com/ja-jp/cards/48156-lord-godfrey?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%AD%E3%83%BC%E3%83%89%E3%83%BB%E3%82%B4%E3%83%83%E3%83%89%E3%83%95%E3%83%AA%E3%83%BC",
        "https://hearthstone.blizzard.com/ja-jp/cards/777-lord-jaraxxus?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%AD%E3%83%BC%E3%83%89%E3%83%BB%E3%82%B8%E3%83%A3%E3%83%A9%E3%82%AF%E3%82%B5%E3%82%B9",
        "https://hearthstone.blizzard.com/ja-jp/cards/103471-reno-lone-ranger?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%83%AD%E3%83%BC%E3%83%B3%E3%83%AC%E3%83%B3%E3%82%B8%E3%83%A3%E3%83%BC%E3%83%BB%E3%83%AC%E3%83%8E",
        "https://hearthstone.blizzard.com/ja-jp/cards/859-twisting-nether?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E6%8D%BB%E3%81%98%E3%82%8C%E3%81%97%E5%86%A5%E7%95%8C",
        "https://hearthstone.blizzard.com/ja-jp/cards/581-alexstrasza?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E3%82%A2%E3%83%AC%E3%82%AF%E3%82%B9%E3%83%88%E3%83%A9%E3%83%BC%E3%82%B6",
        "https://hearthstone.blizzard.com/ja-jp/cards/97702-sargeras-the-destroyer?set=wild&sort=manaCost%3Aasc%2Cname%3Aasc%2Cclasses%3Aasc%2CgroupByClass%3Aasc%2CgroupByClass%3Aasc&textFilter=%E7%A0%B4%E5%A3%8A%E8%80%85%E3%82%B5%E3%83%AB%E3%82%B2%E3%83%A9%E3%82%B9",
    ]
    img_link_idx = 0
    
    deck_html = ''
    for row in card_rows:
        cost_match = re.search(r'<span class="cardRow-Cost">(\d+)</span>', row)
        name_match = re.search(r'<span class="cardRow-Name.*?">([^<]+)</span>', row)
        img_match = re.search(r'<div class="cardRow-cropImage" style="background-image: url\(&quot;(.*?)&quot;\);"></div>', row)

        count = 1
        count_match = re.search(r'<span class="cardRow-Count ">x(\d)</span>', row)
        if count_match:
            count = int(count_match.group(1))
            
        legendary_match = re.search(r'<span class="cardRow-Count legendary"></span>', row)
        if legendary_match:
            count = 1

        if name_match and img_match:
            card_name = name_match.group(1)
            cost = cost_match.group(1) if cost_match else 'N/A'
            img_url = img_match.group(1)
            
            if "（" in card_name:
                card_name = card_name.split("（")[0]

            if img_url.startswith('http'):
                img_path = img_url
            else:
                img_path = "mainHtml/" + img_url.lstrip("./")

            # Prefer canonical URL if we have a mapping for the localized name
            canonical_url = None
            mapped = config_mapping.get(card_name)
            if mapped:
                cid, slug = mapped
                canonical_url = f"https://hearthstone.blizzard.com/ja-jp/cards/{cid}-{slug}"

            search_url = f"https://hearthstone.blizzard.com/ja-jp/cards?textFilter={urllib.parse.quote(card_name)}"
            final_url = canonical_url or search_url

            # Determine image href: use provided image_links sequence if available
            if img_link_idx < len(image_links):
                img_href = image_links[img_link_idx]
                img_link_idx += 1
            else:
                img_href = final_url

            deck_html += f'''
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <a href="{img_href}" target="_blank">
                    <img src="{img_path}" alt="{card_name}" style="height: 100px; margin-right: 10px;">
                </a>
                <p>Cost: {cost}, Name: <a href="{final_url}" target="_blank">{card_name}</a>, Count: {count}</p>
            </div>
            '''

    # Include UTF-8 meta and a Japanese font stack to avoid PDF garbling
    return f'''
    <html>
    <head>
        <meta charset="utf-8">
        <title>Hearthstone Decklist</title>
        <style>
            body {{ font-family: "Noto Sans JP", "Hiragino Kaku Gothic ProN", "Yu Gothic", Meiryo, "MS PGothic", sans-serif; }}
            a {{ color: #1a73e8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .card-row {{ display:flex; align-items:center; margin-bottom:10px; }}
            .card-row img {{ height:100px; margin-right:10px; }}
        </style>
    </head>
    <body>
        <h1>Decklist</h1>
        {deck_html}
    </body>
    </html>
    '''

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        output_html_path = "decklist.html"

        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        deck_html_output = parse_deck_to_html(html_content)

        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(deck_html_output)

        print(f"Successfully created {output_html_path}")

        # Convert HTML to PDF
        output_pdf_path = "decklist.pdf"
        HTML(string=deck_html_output, base_url=os.path.dirname(os.path.abspath(file_path))).write_pdf(output_pdf_path)
        print(f"Successfully created {output_pdf_path}")
    else:
        print("Please provide the HTML file path as an argument.")
