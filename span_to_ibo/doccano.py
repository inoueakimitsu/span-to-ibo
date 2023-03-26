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


def text_to_ibo_style_record_list(
        text: str, tokenizer: janome.tokenizer.Tokenizer, label_place_holder: str = "O"
        ) -> List[IBOStyleRecord]:
    """Convert text to IBO style record list.

    Args:
        text (str):
            sentence or multiple sentence as a string
            includes multiple phrases.
            each phrase is separated by a space.
            ex. "東京都渋谷区渋谷 ２丁目２−８ 渋谷マークシティ"
        label_place_holder (str): label place holder
        tokenizer (janome.tokenizer.Tokenizer):
            tokenizer
    
    Returns:
        iob_record_list (List[IBOStyleRecord]):
            IBO style record list
    """
    iob_record_list = []
    for token in tokenizer.tokenize(text):
        iob_record_list.append({
            "word": token.surface,
            "label": label_place_holder,
            "pos_tag": token.part_of_speech.split(",")[0],
            "pos_tag[:2]": ",".join(token.part_of_speech.split(",")[:2]),
            "pos_tag_all": token.part_of_speech,
            "BOS": False,
            "EOS": False,
        })

    # set BOS and EOS
    if len(iob_record_list) > 0:
        iob_record_list[0]["BOS"] = True
        iob_record_list[-1]["EOS"] = True

    return iob_record_list


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


def doccano_exported_df_to_ibo_style_df_list(
    doccano_exported_df: DoccanoExportedDf, tokenizer: janome.tokenizer.Tokenizer
) -> List[IBOStyleDf]:
    """Convert doccano exported dataframe to list of IBO style dataframe.

    Args:
        doccano_exported_df (pd.DataFrame): doccano exported dataframe
        tokenizer (janome.tokenizer.Tokenizer): tokenizer

    Returns:
        df_ibo_list (List[pd.DataFrame]): list of IBO style dataframe
    """
    df_ibo_list = []

    for _, sentence_row in doccano_exported_df.iterrows():
        cursor_position = 0
        text = sentence_row.text
        labels = sentence_row.label
        tokens = []
        previous_label_index = -1
        for token in tokenizer.tokenize(text):
            
            label = [(i_label, label) for i_label, label in enumerate(labels) if label[0] <= cursor_position and cursor_position < label[1]]
            if len(label) == 1:
                i_label, label = label[0]
                label = label[2]
                if previous_label_index == i_label:
                    label = "I-" + label
                else:
                    label = "B-" + label
                    previous_label_index = i_label
            elif len(label) == 0:
                label = "O"
            else:
                raise ValueError(label)

            tokens.append({
                "word": token.surface,
                "label": label,
                "pos_tag": token.part_of_speech.split(",")[0],
                "pos_tag[:2]": ",".join(token.part_of_speech.split(",")[:2]),
                "pos_tag_all": token.part_of_speech,
                "BOS": False,
                "EOS": False,
            })
            cursor_position += len(token.surface)

        df_ibo_list.append(pd.DataFrame(tokens))
    
    return df_ibo_list


def ibo_style_df_list_to_list_of_ibo_style_record_list(
    ibo_style_df_list: List[List[IBOStyleDf]]
) -> List[List[IBOStyleRecord]]:
    """Convert list of IBO style dataframe to list of list of IBO style record.

    Args:
        ibo_style_df_list (List[pd.DataFrame]): list of IBO style dataframe

    Returns:
        list_of_ibo_style_record_list (List[List[IBOStyleRecord]]): list of IBO style record list
    """
    list_of_ibo_style_record_list: List[List[IBOStyleRecord]] = []

    for ibo_style_df in ibo_style_df_list:
        list_of_ibo_style_record_list.append(ibo_style_df.to_dict("records"))

    return list_of_ibo_style_record_list


def save_list_of_ibo_style_record_list(
    output_path: str, list_of_ibo_style_record_list: List[List[IBOStyleRecord]]
) -> None:
    """Save list of IBO style record list to output path in JSON format.

    Args:
        output_path (str): output path
        list_of_ibo_style_record_list (List[List[IBOStyleRecord]]): list of IBO style record list
    """
    try:
        with open(output_path, "w") as f:
            json.dump(list_of_ibo_style_record_list, f, ensure_ascii=False, indent=4)
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
    ibo_style_df_list = doccano_exported_df_to_ibo_style_df_list(doccano_exported_df, tokenizer)
    list_of_ibo_style_record_list = ibo_style_df_list_to_list_of_ibo_style_record_list(ibo_style_df_list)
    save_list_of_ibo_style_record_list(args.output_path, list_of_ibo_style_record_list)


if __name__ == "__main__":
    main()
