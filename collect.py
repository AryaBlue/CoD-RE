"""Refresh this repo from the working projects, then review with `git status` and commit.

Copies only our own reverse-engineering output (struct headers, size probes, OAT
patches, binary-format decoders, notes). Never game files or dumped assets.
"""
import shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
CONV = Path(r'E:\Documents\BO1MapConverter')

# dest folder -> source files. games/<game>/ holds game-specific RE, shared/ and converter/ the rest
COPIES = {
    'games/t5-bo1/headers': [CONV / 'research' / n for n in ('T5.h', 'T5_Assets.h')],
    'games/t6-bo2/headers': [CONV / 'research' / 'probe' / 'T6_Assets.h'],
    'shared/probe': [CONV / 'research' / 'probe' / n for n in ('sizes.cpp', 'sizes.txt', 'b.bat')],
    'shared/tools': [CONV / 'research' / n for n in ('structdiff.py', 'structdiff.txt')],
    'shared/notes': [CONV / 'research' / 'bo1_to_bo2_porting.md'],  # b2w's handoff log stays out, other people's paths
    'games/t6-bo2/notes/engine': [CONV / 'research' / n for n in ('t6_cbuf.md', 't6_sv_sendservercommand.md', 't6_sound_playsound.md')],
    'games/t6-bo2/notes/render': [CONV / 'research' / 't6_materials_runtime.md'],
    'games/t6-bo2/notes/tables': sorted(f for f in (CONV / 'research' / 't6_renderer').glob('t6*') if f.is_file()),
    'games/t6-bo2/t6match': sorted(f for f in (CONV / 'research' / 't6_renderer' / 't6match').iterdir() if f.suffix in ('.py', '.java')),
    'converter': [CONV / 'run_bo1.py', CONV / 'README.md'],
    'converter/tools': sorted((CONV / 'tools').glob('*.py')),
    # ZM Workshop's code stays private
}
# notes lose their game prefix here, the folder already says which game
RENAME = {
    't6_cbuf.md': 'cbuf.md', 't6_sv_sendservercommand.md': 'sv_sendservercommand.md',
    't6_sound_playsound.md': 'sound_playsound.md', 't6_materials_runtime.md': 'materials_runtime.md',
}

# local OAT checkout under CONV -> its home here. one changes.patch per checkout, filed under the game it mostly serves
OAT_TREES = {
    'oat': HERE / 'shared' / 'oat-patches' / 'oat',
    'oat-bsp': HERE / 'games' / 't5-bo1' / 'oat-bsp',
    'oat_ext': HERE / 'shared' / 'oat-patches' / 'oat_ext',
}
# games/t6-bo2/oatfork/ is a manual snapshot (lives in F:\ClaudeBench\oatfork), refresh it by hand
CONVERTER_TREE = 'b2w_bo1'  # our BO1 converter, diffed against upstream B2W (github.com/Ticass/B2W)
SKIP_NEW = ('.png', '.jpg', '.dds', '.iwi', '.webp')  # art isn't ours to publish


def git(tree, *args):
    return subprocess.run(['git', '-C', str(tree), *args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace', check=True).stdout


def main():
    for dest, sources in COPIES.items():
        out = HERE / dest
        out.mkdir(parents=True, exist_ok=True)
        for src in sources:
            if src.is_file():
                shutil.copy2(src, out / RENAME.get(src.name, src.name))
            else:
                print('missing', src)
    trees = list(OAT_TREES.items())
    trees.append((CONVERTER_TREE, HERE / 'converter' / 'b2w-patch'))
    for name, out in trees:
        tree = CONV / name
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        base = git(tree, 'rev-parse', 'HEAD').strip()
        if 'upstream' in git(tree, 'remote').split():
            base = git(tree, 'merge-base', 'HEAD', 'upstream/main').strip()  # diff against where we left upstream
        added = git(tree, 'diff', '--name-only', '--diff-filter=A', base).splitlines()
        (out / 'BASE_COMMIT').write_text(base + '\n')
        (out / 'changes.patch').write_text(
            git(tree, 'diff', '--binary', base, '--', '.', *[f':(exclude){rel}' for rel in added]), encoding='utf-8')
        for rel in added + git(tree, 'ls-files', '--others', '--exclude-standard').splitlines():
            if not rel.startswith('src/') or rel.lower().endswith(SKIP_NEW):
                continue  # build output and art stay out
            if name != CONVERTER_TREE and rel.startswith('src/waw2bo2/'):
                continue  # converter copies inside OAT trees
            target = out / 'new' / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tree / rel, target)
    subprocess.run([sys.executable, str(HERE / 'shared' / 'tools' / 'index.py')], check=True)
    print('done')


if __name__ == '__main__':
    main()
