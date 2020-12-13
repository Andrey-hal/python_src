import os
import sys
path = os.environ['path']
done_path = []
for p in path.split(';'):
    if '''bin\\Py''' not in p and p != '' and 'ython' not in p:
        done_path.append(p)
if len(sys.argv) == 1:
    stdout = os.popen('''setx /M PATH "{}"'''.format(';'.join(done_path)))
    print(stdout.read())
else :
    stdout = os.popen('''setx /M PATH "{};{}"'''.format(';'.join(done_path),sys.argv[1]))
    print(stdout.read())
    if len(sys.argv) == 3:
        stdout = os.popen('''setx /M PYTHONPATH "{}"'''.format(sys.argv[2].replace('"','')))
        print(stdout.read())
print('done')