import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin


def scrape_url(url: str) -> dict:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for s in soup(["script", "style", "nav", "footer", "header"]):
            s.decompose()

        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            meta_desc = meta.get("content", "")

        headings = []
        for tag in ["h1", "h2", "h3"]:
            for el in soup.find_all(tag):
                text = el.get_text(strip=True)
                if text and len(text) > 5:
                    headings.append(f"{tag.upper()}: {text}")

        paragraphs = []
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                paragraphs.append(text)

        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if text and href and not href.startswith("#") and not href.startswith("javascript"):
                links.append({"text": text[:100], "href": href})

        # Extract images
        images = []
        seen_src = set()
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if not src or src.startswith("data:"):
                continue
            abs_src = urljoin(url, src)
            if abs_src not in seen_src:
                seen_src.add(abs_src)
                alt = img.get("alt", "")
                images.append({
                    "src": abs_src,
                    "alt": alt[:100] if alt else "",
                    "width": img.get("width", ""),
                    "height": img.get("height", ""),
                })

        # Extract video elements
        videos = []
        for video in soup.find_all("video"):
            src = video.get("src")
            if src:
                videos.append({"src": urljoin(url, src), "type": "video"})
            for source in video.find_all("source"):
                s = source.get("src")
                if s:
                    videos.append({"src": urljoin(url, s), "type": "video"})
        for iframe in soup.find_all("iframe", src=True):
            s = iframe["src"]
            if any(d in s for d in ["youtube.com/embed", "player.vimeo.com"]):
                videos.append({"src": s, "type": "embed"})

        body_text = " ".join(paragraphs[:30])
        word_count = len(body_text.split())

        return {
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "headings": headings[:15],
            "summary": body_text[:3000],
            "paragraph_count": len(paragraphs),
            "word_count": word_count,
            "links_found": len(links),
            "sample_links": links[:10],
            "images": images[:10],
            "videos": videos[:5],
        }
    except requests.Timeout:
        return {"url": url, "error": "Request timed out"}
    except requests.RequestException as e:
        return {"url": url, "error": str(e)}
    except Exception as e:
        return {"url": url, "error": f"Parse error: {str(e)}"}
