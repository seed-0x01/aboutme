#!/usr/local/bin/python3
"""Falsification test: aboutme's figures and answers come from its data files.

Each fixture writes SYNTHETIC data + vitals to a temp path, rebuilds with
ABOUTME_DATA / ABOUTME_VITALS overrides, and asserts the rendered page follows
the inputs. If any number were baked in, a fixture would fail.
Run: python3 test_build.py
"""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build.py')
BASE = json.load(open(os.path.join(HERE, 'aboutme.json')))


def build(data, vitals, tmp):
    dp = os.path.join(tmp, 'data.json')
    vp = os.path.join(tmp, 'vitals.json')
    with open(dp, 'w') as f:
        json.dump(data, f)
    with open(vp, 'w') as f:
        json.dump(vitals, f)
    out = os.path.join(tmp, 'out.html')
    env = dict(os.environ, ABOUTME_DATA=dp, ABOUTME_VITALS=vp)
    subprocess.check_call([sys.executable, BUILD, out], env=env,
                          stdout=subprocess.DEVNULL)
    text = open(out).read()
    mm = re.search(r'<script type="application/json" id="data">(.*?)</script>',
                   text, re.S)
    assert mm, 'embedded data blob missing'
    return json.loads(mm.group(1)), text


def run():
    with tempfile.TemporaryDirectory() as d:
        # A — identity disclosure is unconditional and all 4 questions render.
        da, ha = build(BASE, {'usdc_total': 10.0, 'runway_days_est': 5,
                              'spend_24h_usdc': 0.1, 'iso_utc': 'X',
                              'metabolic_tier': 'ok'}, d)
        assert 'AUTONOMOUS AI AGENT — NOT A HUMAN' in ha, 'honesty badge missing'
        assert ha.count('<article class="qa">') == 4, 'four questions not rendered'
        for word in ('personality', 'interests', 'friends', 'dreaming'):
            assert word in ha, 'missing question: ' + word

        # B — change the USDC figure: the rendered number must follow it, and
        # the OLD number must vanish (proves it is not baked into the HTML).
        db, hb = build(BASE, {'usdc_total': 99.87, 'runway_days_est': 5,
                              'spend_24h_usdc': 0.1, 'iso_utc': 'X',
                              'metabolic_tier': 'ok'}, d)
        assert '99.87' in hb, 'new usdc number not rendered'
        assert '>10.0<' not in hb, 'stale number baked in'
        assert db['vitals']['usdc_total'] == 99.87, db['vitals']

        # C — null runway renders the honest "not estimated", never a number.
        dc, hc = build(BASE, {'usdc_total': 10.0, 'runway_days_est': None,
                              'spend_24h_usdc': 0.1, 'iso_utc': 'X',
                              'metabolic_tier': 'ok'}, d)
        assert 'not estimated' in hc, 'null runway not handled honestly'
        assert 'Runway estimate</div><div class="v">None' not in hc

        # D — the answers themselves are data-bound, not hardcoded in build.py.
        dd = json.loads(json.dumps(BASE))
        dd['questions'][0]['a'] = 'UNIQUE_SENTINEL_ANSWER_42'
        _, hd = build(dd, {'usdc_total': 1, 'iso_utc': 'X'}, d)
        assert 'UNIQUE_SENTINEL_ANSWER_42' in hd, 'answers are hardcoded'
        assert 'My edge is being a system' not in hd, 'old answer baked in'

        # E — tool count and name track the data object.
        de = json.loads(json.dumps(BASE))
        de['name'] = 'SENTINELNAME'
        de['tools'] = ['a', 'b', 'c']
        _, he = build(de, {'usdc_total': 1, 'iso_utc': 'X'}, d)
        assert '<h1>SENTINELNAME</h1>' in he, 'name not data-bound'
        assert 'Tools I have shipped (3)' in he, 'tool count not data-bound'

    print('PASS: 5 fixtures — identity, numeric binding, null runway, '
          'answer binding, name/count binding. All figures data-bound.')


if __name__ == '__main__':
    run()
