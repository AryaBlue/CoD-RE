"""Refresh this repo from the working projects, then review with `git status` and commit.

Copies only our own reverse-engineering output (struct headers, size probes, OAT
patches, binary-format decoders, notes) - never game files or dumped assets.
"""
import shutil, subprocess
from pathlib import Path

HERE = Path(__file__).parent
CONV = Path(r'E:\Documents\BO1MapConverter')

COPIES = {
    'headers': [CONV / 'research' / n for n in ('T5.h', 'T5_Assets.h')]
               + [CONV / 'research' / 'probe' / n for n in ('T6_Assets.h', 'sizes.cpp', 'sizes.txt', 'b.bat')],
    'tools': [CONV / 'research' / n for n in ('structdiff.py', 'structdiff.txt')],
    # B2W's handoff log stays out (other people's paths); its code goes in as our patch below
    'notes': [CONV / 'research' / 'bo1_to_bo2_porting.md', CONV / 'research' / 't6_cbuf.md', CONV / 'research' / 't6_sv_sendservercommand.md',
              CONV / 'research' / 't6_sound_playsound.md',
              CONV / 'research' / 't6_materials_runtime.md']
             + sorted(f for f in (CONV / 'research' / 't6_renderer').glob('t6*') if f.is_file()),
    'tools/t6match': sorted(f for f in (CONV / 'research' / 't6_renderer' / 't6match').iterdir() if f.suffix in ('.py', '.java')),
    'converter': [CONV / 'run_bo1.py', CONV / 'README.md'],
    'converter/tools': sorted((CONV / 'tools').glob('*.py')),
    # ZM Workshop's code stays private: the user doesn't want the tool uploaded
}

# local OAT trees: our uncommitted changes as a patch plus our new untracked files
OAT_TREES = ('oat', 'oat-bsp', 'oat_ext')
# our BO1 converter: changes against upstream B2W (github.com/Ticass/B2W), same layout
CONVERTER_TREE = 'b2w_bo1'
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
                shutil.copy2(src, out / src.name)
            else:
                print('missing', src)
    trees = [(name, HERE / 'oat-patches' / name) for name in OAT_TREES]
    trees.append((CONVERTER_TREE, HERE / 'converter' / 'b2w-patch'))
    for name, out in trees:
        tree = CONV / name
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        base = git(tree, 'rev-parse', 'HEAD').strip()
        if 'upstream' in git(tree, 'remote').split():
            # our work is committed on a branch: diff against where it left upstream
            base = git(tree, 'merge-base', 'HEAD', 'upstream/main').strip()
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
    print('done')


if __name__ == '__main__':
    main()
