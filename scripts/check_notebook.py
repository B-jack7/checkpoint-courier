"""Run the CPU notebook example against the installed local package."""
import json
from pathlib import Path

notebook = json.loads((Path(__file__).resolve().parents[1] / 'notebooks/quickstart.ipynb').read_text(encoding='utf-8'))
namespace = {}
for index, cell in enumerate(notebook['cells']):
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        compiled = compile(source, f'cell-{index}', 'exec')
        if index != 1:  # Skip remote installation; test the locally installed package.
            exec(compiled, namespace)
print('Notebook example passed (remote install skipped).')
