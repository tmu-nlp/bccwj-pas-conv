#!/usr/bin/python
# -*- coding: utf-8 -*-

from bin.env_cabocha import envCaboCha

def main():
    env = envCaboCha()
    model_dir = env.cabocha_model_dir()

    with open('bin/unidic_cabocharc', 'w') as f:
        f.write('charset = utf8\n')
        f.write('posset = UNIDIC\n')
        f.write('output-format = 0\n')
        f.write('input-layer = 0\n')
        f.write('output-layer = 4\n')
        f.write('ne = 1\n')
        f.write('parser-model = %s/dep.unidic.model\n' % model_dir)
        f.write('chunker-model = %s/chunk.unidic.model\n' % model_dir)
        f.write('ne-model = %s/ne.unidic.model\n' % model_dir)
    print "Done."

if __name__ == '__main__':
    main()
