# Span to IBO

This is a script to convert the output file of `doccano` 
to a format that is easy to handle with `sklearn-crfsuite`.

## Usage

```bash
python doccano.py --input_path <path to doccano exported jsonl file> --output_path <path to output file>
```

## Input file format

The input file is a jsonl file exported from `doccano`.

```json
{"text": "東京都渋谷区渋谷 ２丁目２−８ 渋谷マークシティ", "labels": [[0, 9, "LOC"]]}
{"text": "東京都渋谷区神南 １丁目１−１", "labels": [[0, 7, "LOC"]]}
...
```

## Output file format

The output file is a json file of the following format:

```json
[
    [
        {"word": "東京都", "label": "B-LOC", "pos_tag": "名詞", "pos_tag[:2]": "名詞,固有名詞", "pos_tag_all": "名詞,固有名詞,地域,一般,*,*,東京都,トウキョウト,トーキョート", "BOS": true, "EOS": false},
        {"word": "渋谷区", "label": "I-LOC", "pos_tag": "名詞", "pos_tag[:2]": "名詞,固有名詞", "pos_tag_all": "名詞,固有名詞,地域,一般,*,*,渋谷区,シブヤク,シブヤク", "BOS": false, "EOS": false},
        ...
    ],
    ...,
]
```

## Reference

This program is mainly based on the following repository.
https://github.com/ToshihikoSakai/jsontoconll

All mistakes in this script are mine.
