import ipaddress
import re
import socket
import ssl
from http.cookiejar import CookieJar
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlsplit, urlunsplit
from urllib.error import URLError
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener


def encode_web_url(url):
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").encode("idna").decode("ascii")
    if ":" in hostname:
        hostname = f"[{hostname}]"
    netloc = hostname + (f":{parsed.port}" if parsed.port else "")
    return urlunsplit((parsed.scheme, netloc, quote(parsed.path, safe="/%:@!$&'()*+,;=-._~"), quote(parsed.query, safe="%=&/?@!$'()*+,;:-._~"), ""))


def validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("공개 웹사이트의 http/https 주소를 입력해주세요.")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("표준 웹사이트 포트만 지원합니다.")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("로컬 또는 내부 네트워크 주소는 가져올 수 없습니다.")


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        hostname = urlparse(newurl).hostname or ""
        if hostname == "queue-it.net" or hostname.endswith(".queue-it.net"):
            raise ValueError("사이트의 접속 대기열 때문에 본문을 읽을 수 없습니다. 원문을 직접 붙여 넣어주세요.")
        return super().redirect_request(req, fp, code, msg, headers, encode_web_url(newurl))


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.in_title = False
        self.title = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer", "noscript"}:
            self.skip += 1
        if tag == "title":
            self.in_title = True
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer", "noscript"}:
            self.skip = max(0, self.skip - 1)
        if tag == "title":
            self.in_title = False
        if tag in {"p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        elif not self.skip:
            self.parts.append(data)


def open_public_page(url):
    cookies = CookieJar()
    request = Request(encode_web_url(url), headers={"User-Agent": "Mozilla/5.0 (compatible; ON-AIR/1.0)"})
    handlers = [ProxyHandler({}), HTTPCookieProcessor(cookies), PublicRedirect()]
    try:
        return build_opener(*handlers).open(request, timeout=12)
    except URLError as exc:
        if not isinstance(exc.reason, ssl.SSLError) or "HANDSHAKE_FAILURE" not in str(exc.reason):
            raise
        # Some public sites require RSA ciphers absent from Python's defaults.
        # Retain certificate/hostname verification and TLS 1.2 or newer.
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers("DEFAULT")
        return build_opener(*handlers, HTTPSHandler(context=context)).open(request, timeout=12)


def collect_sources(sources):
    collected = []
    for source in sources:
        title, text, url = source.title, source.text, source.url.strip()
        if url:
            try:
                validate_url(url)
                # Naver's desktop page contains only a frame; the mobile URL
                # serves the same public post with its article text inline.
                parsed = urlparse(url)
                if parsed.hostname in {"blog.naver.com", "www.blog.naver.com"}:
                    parts = parsed.path.strip("/").split("/")
                    params = parse_qs(parsed.query)
                    if len(parts) == 2 and parts[1].isdigit():
                        fetch_url = f"https://m.blog.naver.com/{parts[0]}/{parts[1]}"
                    elif params.get("blogId") and params.get("logNo"):
                        fetch_url = "https://m.blog.naver.com/PostView.naver?" + urlencode({"blogId": params["blogId"][0], "logNo": params["logNo"][0]})
                    else:
                        fetch_url = url
                    validate_url(fetch_url)
                else:
                    fetch_url = url
                with open_public_page(fetch_url) as response:
                    content_type = response.headers.get_content_type()
                    if content_type not in {"text/html", "text/plain"}:
                        raise ValueError("HTML 또는 텍스트 웹페이지만 지원합니다.")
                    raw = response.read(2_000_001)
                    if len(raw) > 2_000_000:
                        raise ValueError("웹페이지가 너무 큽니다.")
                    body = raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
                if content_type == "text/html":
                    parser = ArticleParser()
                    parser.feed(body)
                    text = "\n".join(re.sub(r"\s+", " ", p).strip() for p in "".join(parser.parts).splitlines() if len(p.strip()) >= 25)
                    title = title or "".join(parser.title).strip()
                else:
                    text = body
            except Exception as exc:
                raise ValueError(f"소스를 가져오지 못했습니다 ({url}): {exc}") from exc
        if len(text.strip()) < 30:
            raise ValueError(f"'{title or url or '자료'}'의 본문이 부족합니다. 본문을 직접 붙여 넣어주세요.")
        collected.append({"title": title or url or f"자료 {len(collected) + 1}", "url": url, "text": text[:12000]})
    return collected


def collect_available_sources(sources):
    collected, warnings = [], []
    for source in sources:
        try:
            collected.extend(collect_sources([source]))
        except ValueError as exc:
            warnings.append(str(exc))
    if sources and not collected:
        raise ValueError("선택한 출처의 본문을 가져오지 못했습니다. 다른 출처를 선택하거나 본문을 붙여 넣어주세요. " + " / ".join(warnings))
    return collected, warnings


def search_sources(query):
    from ddgs import DDGS

    results = DDGS(timeout=12).text(query, region="kr-ko", safesearch="moderate", max_results=10)
    found = []
    seen = set()
    for item in results:
        url = item.get("href", "")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or url in seen:
            continue
        seen.add(url)
        found.append({"title": item.get("title", url), "url": url, "snippet": item.get("body", ""), "domain": parsed.hostname})
    return found
