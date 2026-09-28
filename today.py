#!/usr/bin/env python3
"""Render dark_mode.svg / light_mode.svg: a neofetch-style profile card with live age and GitHub stats."""
import datetime
import json
import os
import textwrap
import time
import urllib.error
import urllib.request

USER = 'Samuel-A-Berlin'
BIRTHDAY = datetime.date(2006, 4, 24)
CROP = 15 # columns cut from each side of the art
W = 73    # info line width in characters

ART = r"""
                                    ##%%%%@@@@
                                 #%%%@%%@@@@@@@@
                              %%%%@@@@@@@@@%%@@@@@@@%
                             %%%@@@@@@@@@@@@%%%@@@@@@@@
                            @@@%%@@@@@@@@@@@@@@@@@@@@@@
                           @%%%%%%@@@@@@@@@@@@@@@@@@@@@
                          %%%%#%%%%@@@@@@@@@%%%%%#%@@@@%
                          %%%%%%%%%%%@@@@@%#####*+#%@@@@@
                          %%%%%%%###%%%%%##*++**+++#%@@%
                          @%%%%#########*=--=***++**%%@%
                           @%%%#*+=+**+++--+++***++*#*#
                           %%****++*++--=+=+=---==++*==
                            %*=+*+=--===+*=*+=----=++==
                             #+=**+=====++==*=--==++-==
                              *++*++==-=+++++=--==+*=
                             @%%%#+++==+**=+**+==+++
                               ##%+++=+**+=+*#+===+*
                                  **++==++++=====++
                                  ***++=-======+**
                                 #*++++**++++*#*+*
                             =+*#**+=--======+==+*
                         ::-----**++=-------====+++-=
                  =---:::::::::..-===--::------=+++-::--:
             +=====---:::::..::.....:--:::::::-===:.:.::::.::
           ==--::::::::::......................   ...:::::::::::::
          -:::...:......::.............        .. ...............::-
        -::.:.:..:.........::..............       .. ...............:-
        :-.:.................:..............   ..    ............  :.:-
       :--....... ..........:-++==-.......           ............  ....-
      ::-:.......... ....:*+=+**+==++. .:=:     :==-............. ......:
     :::-:...:..........====-=======-   .:=-:  .**+=----......... ........
     :.:--....::.......-====++**+--+=   -++-. .=%%%%#*.- ........ . ......:
    -:::::.......:.....+=========+===-:  =.=::*:-+%%#*.   .....:. ....... .
   +::.:::............=*==-===+*==+:     =.=.-=:..:..    ......:.. ....... .
  =-:::::::......:...=*+==+*+++=+*+=.    -:+*=::*- .-+=   ................. .
  =-:::::::......:.:+**+=+*#**%##*:.     .:+= +#*###*=+. ....:.:... .........:
  -::::::::......-+*+++*+**#%%%%#-=-.     .=*=-=+#%%%#*  ....:.:.............:
  --::::::.....:*#*+==++**#%%%%%%*=..    . =%***###%%#+  ....:.:..............-
  +=::::::...:+***++++++#::%%%%%%#+:.    ..=#+*=#+#%%#=  ..:::::..............:-
    %#*=-::-+***++++==+*:.:%%%%**%*-..  .-=+%%%%%%%%%#-. .::---:................
"""
_art = textwrap.dedent(ART).strip('\n').splitlines()
_wide = max(map(len, _art))
ART_LINES = [line[CROP:_wide - CROP].rstrip() for line in _art[:-2]]

THEMES = {
    'dark_mode.svg': dict(bg='#161b22', fg='#c9d1d9', key='#ffa657', value='#a5d6ff', cc='#616e7f', add='#3fb950', dele='#f85149'),
    'light_mode.svg': dict(bg='#f6f8fa', fg='#24292f', key='#953800', value='#0a3069', cc='#c2cfde', add='#1a7f37', dele='#cf222e'),
}


def plural(n, word):
    return f'{n} {word}' + ('' if n == 1 else 's')


def age(today):
    y, m, d = today.year - BIRTHDAY.year, today.month - BIRTHDAY.month, today.day - BIRTHDAY.day
    if d < 0:
        m -= 1
        d += (today.replace(day=1) - datetime.timedelta(days=1)).day
    if m < 0:
        y, m = y - 1, m + 12
    return f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(d, 'day')}"


def api(url, body=None):
    req = urllib.request.Request(url, json.dumps(body).encode() if body else None,
                                 {'Authorization': f"bearer {os.environ['GH_TOKEN']}"})
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read() or 'null')


def gql(query, **variables):
    _, out = api('https://api.github.com/graphql', {'query': query, 'variables': variables})
    if out.get('errors'):
        raise RuntimeError(out['errors'])
    return out['data']['user']


def stats():
    u = gql('query($l:String!){user(login:$l){id followers{totalCount} repositories(ownerAffiliations:OWNER){totalCount}'
            ' repositoriesContributedTo(includeUserRepositories:true,contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY,PULL_REQUEST_REVIEW]){totalCount}}}',
            l=USER)
    # ponytail: first 100 repos only, paginate when there are more
    repos = gql('query($l:String!,$id:ID!){user(login:$l){repositories(first:100,ownerAffiliations:[OWNER,COLLABORATOR,ORGANIZATION_MEMBER]){nodes{'
                'nameWithOwner isFork stargazerCount owner{login} defaultBranchRef{target{...on Commit{history(author:{id:$id}){totalCount}}}}}}}}',
                l=USER, id=u['id'])['repositories']['nodes']
    add = dele = 0
    for r in repos:
        if r['isFork'] or not r['defaultBranchRef']:
            continue
        for _ in range(10):  # GitHub answers 202 while it builds the stats
            try:
                code, contributors = api(f"https://api.github.com/repos/{r['nameWithOwner']}/stats/contributors")
            except urllib.error.HTTPError:
                code, contributors = 0, None
            if code != 202:
                break
            time.sleep(3)
        for c in contributors or []:
            if (c.get('author') or {}).get('login') == USER:
                add += sum(w['a'] for w in c['weeks'])
                dele += sum(w['d'] for w in c['weeks'])
    return dict(
        repos=u['repositories']['totalCount'],
        contrib=u['repositoriesContributedTo']['totalCount'],
        stars=sum(r['stargazerCount'] for r in repos if r['owner']['login'] == USER),
        commits=sum(r['defaultBranchRef']['target']['history']['totalCount'] for r in repos if r['defaultBranchRef']),
        followers=u['followers']['totalCount'],
        add=add, dele=dele)


def kv(key, val, width=W):
    segs = [(val, 'value')] if isinstance(val, str) else val
    dots = width - len(key) - sum(len(t) for t, _ in segs) - 5
    return [('. ', 'cc'), (key, 'key'), (':', 'fg'), (' ' + '.' * dots + ' ', 'cc')] + segs


def pair(k1, v1, k2, v2, left=41):
    return kv(k1, v1, left) + [(' | ', 'fg')] + kv(k2, v2, W - left - 1)[1:]


def title(text):
    return [(text + ' -' + '—' * (W - len(text) - 2), 'fg')]


def info(s, today):
    return [
        title('samuel@berlin'),
        kv('OS', 'macOS Tahoe 26.5'),
        kv('Uptime', age(today)),
        kv('Host', 'AfterQuery'),
        kv('Kernel', 'SPA (Strategic Project Associate)'),
        kv('Directory', 'San Francisco, California'),
        [('.', 'cc')],
        kv('Harnesses.Agentic', 'Claude Code, Codex, Pi Coding Agent, Prime Agent'),
        kv('Harnesses.IRL', 'Uggs, Baggy Pants, Henleys'),
        [('.', 'cc')],
        kv('Interests.Professional', 'RL, Restructuring, Credit'),
        kv('Interests.Sports', 'Cleveland Cavaliers, Ohio State Football'),
        kv('Interests.Personal', 'NBA 2K, Baking, Climbing, Clash Royale, Star Wars'),
        [],
        title('- Contact'),
        kv('Email.Work', 'samuel@afterquery.com'),
        kv('LinkedIn', 'samuel-berlin'),
        kv('Slack', 'Samuel Berlin'),
        [],
        title('- GitHub Stats'),
        pair('Repos', f"{s['repos']:,} {{Contributed: {s['contrib']:,}}}", 'Stars', f"{s['stars']:,}"),
        pair('Commits', f"{s['commits']:,}", 'Followers', f"{s['followers']:,}"),
        kv('Lines of Code on GitHub', [(f"{s['add'] - s['dele']:,}", 'value'), (' ( ', 'fg'), (f"{s['add']:,}++", 'add'),
                                       (', ', 'fg'), (f"{s['dele']:,}--", 'dele'), (' )', 'fg')]),
    ]


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def svg(theme, lines):
    art_fs, art_lh, fs, ch, pad = 8.5, 10.5, 16, 0.61, 20
    art_h = len(ART_LINES) * art_lh
    lh = max(19, art_h / len(lines))
    info_x = pad + max(map(len, ART_LINES)) * art_fs * ch + 22
    width = round(info_x + W * fs * ch + pad)
    height = round(2 * pad + max(art_h, lh * len(lines)))
    css = ' '.join(f'.{k}{{fill:{v}}}' for k, v in theme.items() if k != 'bg')
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}px" height="{height}px" '
           f'font-family="Consolas,Menlo,\'DejaVu Sans Mono\',monospace" xml:space="preserve">',
           f'<style>{css} text,tspan{{white-space:pre}}</style>',
           f'<rect width="{width}px" height="{height}px" fill="{theme["bg"]}" rx="15"/>',
           f'<text class="fg" font-size="{art_fs}px">']
    out += [f'<tspan x="{pad}" y="{pad + art_fs + i * art_lh}">{esc(l)}</tspan>' for i, l in enumerate(ART_LINES)]
    out.append('</text>')
    for i, segs in enumerate(lines):
        body = ''.join(f'<tspan class="{c}">{esc(t)}</tspan>' for t, c in segs)
        out.append(f'<text x="{info_x:.0f}" y="{pad + fs + i * lh:.1f}" font-size="{fs}px">{body}</text>')
    out.append('</svg>\n')
    return '\n'.join(out)


if __name__ == '__main__':
    assert age(datetime.date(2026, 9, 28)) == '20 years, 5 months, 4 days'
    assert age(datetime.date(2026, 4, 23)) == '19 years, 11 months, 30 days'
    today = datetime.date.today()
    lines = info(stats(), today)
    assert all(sum(len(t) for t, _ in l) in (0, 1, W) for l in lines), 'info line width drift'
    for name, theme in THEMES.items():
        with open(name, 'w') as f:
            f.write(svg(theme, lines))
