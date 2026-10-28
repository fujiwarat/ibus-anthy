#!/usr/bin/env python3

from pathlib import Path
import sys

def generate_emoji_t(emoji_each, emoji_emoji, output):
    result = []
    with open(emoji_each, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#@EMOJI_EMOJI@'):
                with open(emoji_emoji, 'r', encoding='utf-8') as f2:
                    for line2 in f2:
                        if line2.startswith('#'):
                            continue
                        else:
                            result.append(line2)
            else:
                result.append(line)
    with open(output, 'w', encoding='utf-8') as f:
        f.writelines(result)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(f'Generate emoji.t from emoji-each.t and emoji-emoji.t.\n' +
                 f'Usage: {Path(sys.argv[0]).name} ' +
                 f'emoji-each.t emoji-emoji.t emoji.t')
    generate_emoji_t(sys.argv[1], sys.argv[2], sys.argv[3])
