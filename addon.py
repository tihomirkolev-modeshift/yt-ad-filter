from mitmproxy import http
import re
import json
import logging
import sys
import os

log = logging.getLogger("yt-ad-filter")

if os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"):
    log.setLevel(logging.DEBUG)
    _sh = logging.StreamHandler(sys.stdout)
    _sh.setLevel(logging.DEBUG)
    _sh.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    log.addHandler(_sh)
else:
    log.addHandler(logging.NullHandler())

AD_DOMAINS = [
    'doubleclick.net',
    'googleadservices.com',
    'googlesyndication.com',
    'adservice.google.com',
    'imasdk.googleapis.com',
]

AD_URL_PATTERNS = [
    r'/pagead/',
    r'/api/stats/ads',
    r'/ptracking',
    r'/get_midroll_',
    r'[&?]ad_',
    r'adunit=',
    r'ad_type=',
    r'el=adunit',
    r'/pcs/activeview',
    r'/pagead/interaction',
    r'/pagead/adview',
    r'/youtubei/v1/player/ad_break',
    r'/api/stats/engage',
]

AD_VIDEO_PARAMS = [
    'oad=',
    'mdetail=',
    'adformat=',
    'cmo=',
    'cmf=',
]

AD_JSON_KEYS = {
    'adPlacements', 'playerAds', 'adSlots', 'adBreakHeartbeatParams',
    'auxiliaryUi', 'adBreaks', 'adMessages', 'adBreakParams',
    'adTimeOffset', 'linearAds', 'instreamVideoAdRenderer',
    'linearAdSequenceRenderer', 'adPlacementRenderer',
    'serverStitchedDaiAdRenderer', 'adBreakServiceRenderer',
}


def _strip_ad_keys(obj, removed=None):
    if removed is None:
        removed = []
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key in AD_JSON_KEYS:
                del obj[key]
                removed.append(key)
            else:
                _strip_ad_keys(obj[key], removed)
    elif isinstance(obj, list):
        for item in obj:
            _strip_ad_keys(item, removed)
    return removed


_decoder = json.JSONDecoder()


def _strip_html_player_response(text):
    changed = False
    for varname in ('ytInitialPlayerResponse', 'ytInitialData'):
        for sep in ('=', ' ='):
            marker = varname + sep
            idx = text.find(marker)
            if idx == -1:
                continue
            brace_idx = text.find('{', idx + len(marker))
            if brace_idx == -1:
                continue
            try:
                data, rel_end = _decoder.raw_decode(text, brace_idx)
                removed = _strip_ad_keys(data)
                if removed:
                    new_json = json.dumps(data)
                    text = text[:brace_idx] + new_json + text[rel_end:]
                    changed = True
                    log.debug(f"[HTML STRIPPED] {varname}: {removed}")
                else:
                    log.debug(f"[HTML] {varname}: no ad keys found")
            except Exception as e:
                log.debug(f"[HTML ERROR] {varname}: {e}")
            break
    return text, changed


def request(flow: http.HTTPFlow) -> None:
    url = flow.request.pretty_url
    host = flow.request.pretty_host

    if any(d in host for d in AD_DOMAINS):
        log.debug(f"[BLOCKED AD DOMAIN] {url[:120]}")
        flow.response = http.Response.make(204, b"", {"Content-Type": "text/plain"})
        return

    if 'youtube.com' in host or 'googlevideo.com' in host:
        if any(re.search(p, url, re.IGNORECASE) for p in AD_URL_PATTERNS):
            log.debug(f"[BLOCKED AD PATTERN] {url[:120]}")
            flow.response = http.Response.make(204, b"", {"Content-Type": "text/plain"})
            return

        if 'googlevideo.com' in host and '/videoplayback' in url:
            if any(p in url for p in AD_VIDEO_PARAMS):
                log.debug(f"[BLOCKED AD VIDEO] {url[:120]}")
                flow.response = http.Response.make(204, b"", {"Content-Type": "text/plain"})
                return


def response(flow: http.HTTPFlow) -> None:
    host = flow.request.pretty_host
    path = flow.request.path

    if 'youtube.com' in host or 'googlevideo.com' in host or 'ytimg.com' in host:
        if 'alt-svc' in flow.response.headers:
            del flow.response.headers['alt-svc']

    if 'youtube.com' not in host:
        return

    ctype = flow.response.headers.get('content-type', '')

    if 'text/html' in ctype:
        try:
            text = flow.response.text
            new_text, changed = _strip_html_player_response(text)
            if changed:
                flow.response.text = new_text
        except Exception as e:
            log.debug(f"[HTML INTERCEPT ERROR] {e}")

    if '/youtubei/v1/player' in path or '/youtubei/v1/next' in path or '/youtubei/v1/get_watch' in path:
        try:
            data = json.loads(flow.response.content)
            removed = _strip_ad_keys(data)
            if removed:
                new_body = json.dumps(data).encode()
                flow.response.content = new_body
                flow.response.headers['content-length'] = str(len(new_body))
                log.debug(f"[API STRIPPED] {removed}")
        except Exception as e:
            log.debug(f"[API STRIP ERROR] {e}")


log.debug("YouTube Ad Filter loaded")
