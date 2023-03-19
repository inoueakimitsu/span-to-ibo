"""simple script to convert doccano exported jsonl file to IBO style dataset.
"""
import argparse
import re
from pathlib import Path
from typing import Any, List, TypedDict, Union
import json

import janome.tokenizer
import pandas as pd

DoccanoExportedDf = pd.DataFrame
IBOStyleDf = pd.DataFrame

IBOStyleRecord = TypedDict(
    "IBOStyleRecord",
    {
        "word": str,
        "label": str,
        "pos_tag": str,
        "pos_tag[:2]": str,
        "pos_tag_all": str,
        "BOS": bool,
        "EOS": bool,
    },
)


def parse_args() -> Any:
    """Parse command line arguments.

    Returns:
        args (argparse.Namespace): command line arguments
    """
    parser = argparse.ArgumentParser("load doccano exported jsonl file and convert to IBO style")
    parser.add_argument("--input_path", type=str, required=True)
    parser.add_argument("--output_path", type=str, required=True)
    args = parser.parse_args()
    return args


def load_doccano_exported_df(input_path: Union[str, Path]) -> DoccanoExportedDf:
    """Load doccano exported jsonl file.

    Args:
        input_path (str): path to doccano exported jsonl file

    Returns:
        doccano_exported_df (pd.DataFrame): doccano exported dataframe
    """
    input_path = Path(input_path)
    assert input_path.exists()
    assert input_path.is_file()
    return pd.read_json(input_path, orient="records", lines=True)


def convert_text_to_ibo_style_df_list(
        text: str, words: List[str], labels: List[str],
        tokenizer: janome.tokenizer.Tokenizer) -> List[IBOStyleDf]:
    """Convert text to IBO style dataframe list.

    Args:
        text (str):
            sentence or multiple sentence as a string
            includes multiple phrases.
            each phrase is separated by a space.
            ex. "東京都渋谷区渋谷 ２丁目２−８ 渋谷マークシティ"

        words (List[str]): list of phrase
            ex. ["東京都渋谷区渋谷"]
        labels (List[str]): list of label
            ex. ["LOC"]
        tokenizer (janome.tokenizer.Tokenizer):
            tokenizer

    Returns:
        iob_df (pd.DataFrame):
            IBO style dataframe
    """
    assert type(words) == list
    assert type(labels) == list

    if len(labels) == 0:
        return []

    is_B = True

    # ex. iob_row_list = [{"word": "東京都", "label": "B-LOC"}, {"word": "渋谷区", "label": "I-LOC"}]
    iob_row_list = []

    for phrase in text.split():
        # ex. phrase = "東京都渋谷区渋谷"

        # this flag is for skipping the following process
        # when phrase is matched with tag_word
        phrase_matches_with_tag_word = False

        token_in_phrase_list = list(tokenizer.tokenize(phrase))
        # ex. word_in_phrase_list = ["東京都", "渋谷区", "渋谷"]
        for tag_word, tag in zip(words, labels):
            # ex. tag_word = "東京都渋谷区渋谷"
            # ex. tag = "LOC"

            if phrase == tag_word:
                is_B = True
                for token in token_in_phrase_list:
                    if is_B:
                        # The first word is only B-*
                        is_B = False
                        # append "B-*"
                        iob_row_list.append({
                            "word": token.surface,
                            "label": "B-" + tag,
                            "pos_tag": token.part_of_speech.split(",")[0],
                            "pos_tag[:2]": ",".join(token.part_of_speech.split(",")[:2]),
                            "pos_tag_all": token.part_of_speech,
                            })

                    else:
                        # append "I-*"
                        iob_row_list.append({
                            "word": token.surface,
                            "label": "I-" + tag,
                            "pos_tag": token.part_of_speech.split(",")[0],
                            "pos_tag[:2]": ",".join(token.part_of_speech.split(",")[:2]),
                            "pos_tag_all": token.part_of_speech,
                            })

                phrase_matches_with_tag_word = True

                words.remove(tag_word)
                labels.remove(tag)
                break

        # if phrase is not matched with tag_word,
        # append "O" to all words in the phrase
        if not phrase_matches_with_tag_word:
            for token in token_in_phrase_list:
                iob_row_list.append({
                    "word": token.surface,
                    "label": "O",
                    "pos_tag": token.part_of_speech.split(",")[0],
                    "pos_tag[:2]": ",".join(token.part_of_speech.split(",")[:2]),
                    "pos_tag_all": token.part_of_speech,
                    })

    iob_df: IBOStyleDf = pd.DataFrame(iob_row_list)

    if len(iob_df) > 0:
        iob_df["BOS"] = False
        iob_df.loc[iob_df.index[0], "BOS"] = True
        iob_df["EOS"] = False
        iob_df.loc[iob_df.index[-1], "EOS"] = True

    return iob_df


def doccano_exported_df_to_ibo_style_df(
    doccano_exported_df: DoccanoExportedDf, tokenizer: janome.tokenizer.Tokenizer
) -> List[IBOStyleDf]:
    """Convert doccano exported dataframe to list of IBO style dataframe.

    Args:
        doccano_exported_df (pd.DataFrame): doccano exported dataframe
        tokenizer (janome.tokenizer.Tokenizer): tokenizer

    Returns:
        iob_style_df_list (List[pd.DataFrame]): list of IBO style dataframe
    """
    iob_style_df_list: List[IBOStyleDf] = []

    # initialize the temporary dataframe
    doccano_exported_df = doccano_exported_df.copy()

    for _, sentence_row in doccano_exported_df.iterrows():

        current_position: int = 0

        # sort the elements of the list by the start index
        # refer:
        # https://github.com/ToshihikoSakai/jsontoconll/blob/master/jsontoformat.py
        doccano_exported_df['label'] = [sorted(labels) for labels in doccano_exported_df['label']]

        # get the words and labels
        words_labels = [list((sentence_row['text'][label[0]:label[1]], label[2])) for label in sentence_row['label']]
        if len(words_labels) == 0:
            continue

        # split the words and labels
        words, labels = list([list(label) for label in zip(*words_labels)])

        # add spaces around the words
        for word, label in zip(words, labels):
            word_pattern = re.compile(re.escape(word))

            for word_match in word_pattern.finditer(sentence_row["text"]):
                str_list = list(sentence_row["text"])

                # if the word is already surrounded by spaces, skip
                if word_match.start() >= current_position:
                    str_list.insert(int(word_match.end()), " ")
                    str_list.insert(int(word_match.start()), " ")
                    str_list = "".join(str_list)
                    current_position = int(word_match.end())
                    break
                else:
                    str_list = "".join(str_list)

            sentence_row["text"] = str_list

        # combine multiple consecutive blanks into one
        sentence_row["text"] = " ".join(sentence_row["text"].split())
        ibo_style_df = convert_text_to_ibo_style_df_list(
            sentence_row["text"], words, labels, tokenizer)
        iob_style_df_list.append(ibo_style_df)

    return iob_style_df_list


def ibo_style_df_list_to_ibo_style_record_list(
    ibo_style_df_list: List[IBOStyleDf]
) -> List[IBOStyleRecord]:
    """Convert list of IBO style dataframe to list of IBO style record.

    Args:
        ibo_style_df_list (List[pd.DataFrame]): list of IBO style dataframe

    Returns:
        ibo_style_record_list (List[IBOStyleRecord]): list of IBO style record
    """
    ibo_style_record_list: List[IBOStyleRecord] = []

    for ibo_style_df in ibo_style_df_list:
        ibo_style_record_list.extend(ibo_style_df.to_dict("records"))

    return ibo_style_record_list


def save_ibo_style_record_list(
    output_path: str, ibo_style_record_list: List[IBOStyleRecord]
) -> None:
    """Save IBO style record list to output path in JSON format.

    Args:
        output_path (str): output path
        ibo_style_record_list (List[IBOStyleRecord]): list of IBO style record
    """
    try:
        with open(output_path, "w") as f:
            json.dump(ibo_style_record_list, f, indent=4, ensure_ascii=False)
    except FileNotFoundError:
        print("Output path does not exist!")
    except json.JSONDecodeError:
        print("IBO style record list is not in JSON format!")
    except Exception:
        print("Unexpected error occurred!")
        raise


def main():
    args = parse_args()
    tokenizer = janome.tokenizer.Tokenizer()
    doccano_exported_df: DoccanoExportedDf = load_doccano_exported_df(args.input_path)
    ibo_style_df_list = doccano_exported_df_to_ibo_style_df(doccano_exported_df, tokenizer)
    ibo_style_record_list = ibo_style_df_list_to_ibo_style_record_list(ibo_style_df_list)
    save_ibo_style_record_list(args.output_path, ibo_style_record_list)


if __name__ == "__main__":
    main()