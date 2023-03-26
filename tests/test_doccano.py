import pandas as pd
import janome

from span_to_ibo.doccano import doccano_exported_df_to_ibo_style_df_list, DoccanoExportedDf, ibo_style_df_list_to_list_of_ibo_style_record_list

def test_doccano_exported_df_to_ibo_style_df_list():

    df_01 = pd.DataFrame(
        [
            {
                "text": "庭には 2 羽にわとりがいる。",
                "label": [[0, 1, "地名"], [4, 7, "個数"], [7, 11, "対象"]]
            },
            {
                "text": "東京都渋谷区渋谷 ２丁目２−８ 渋谷マークシティ東館",
                "label": [[0, 15, "住所"], [16, 24, "地名"], [24, 26, "地名"]]
            },
        ]
    )
    tokenizer = janome.tokenizer.Tokenizer()
    ibo_style_df_list = doccano_exported_df_to_ibo_style_df_list(df_01, tokenizer)

    print(ibo_style_df_list[0])
    print("---")
    print(ibo_style_df_list[1])

    list_of_ibo_style_record_list = \
        ibo_style_df_list_to_list_of_ibo_style_record_list(ibo_style_df_list)

    print("===")
    print(list_of_ibo_style_record_list)
