# AION2 HUD Editor & Dat Decoder ⚙️

[🇺🇸 English](README.md) | [🇰🇷 한국어](README_ko.md) | [🇨🇳 简体中文](README_zh.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Unreal Engine](https://img.shields.io/badge/Unreal_Engine-5-black)

AION2の `DeviceSetting.dat` ファイルをデコード、プレビュー、および編集するためのスタンドアロンのリバースエンジニアリングツールです。
クライアントのローカルHUD制限をバイパスし、複数のキャラクター間でHUDレイアウトとチャットタブ設定を自由にコピー、バックアップ、および変更できます。クライアントパッチによる未解析のヘッダーに対する仮想ID割り当てのフェイルセーフ機能も備わっています。

*(ここに10秒間のデモGIFを挿入: .datを開く -> キャラクター選択 -> レイアウトのコピー -> 保存)*

## 📥 クイックダウンロード
ソースコードからコンパイルする手間を省きたい場合は、コンパイル済みの実行ファイルを直接ダウンロードしてください:
👉 **[AION2_HUD_Editor_V2.exe のダウンロード (v2.0)](https://github.com/victoriousian/AION2_HUD_Editor_V2/releases/tag/v2.0)**

## ⚠️ 免責事項
これは非公式のコミュニティ主導のリバースエンジニアリングツールです。クライアントファイル（`.dat`）の変更は完全に自己責任で行ってください。必ず元の設定のバックアップを保管してください。ツールは保存時に自動的に `.bak` ファイルを作成します。

## 🚀 主な機能
* **XOR & UTF-16LE/UTF-8 デコード:** AION2のローカルセーブデータのハイブリッドコンテナ構造を完全にアンパックします。
* **仮想IDリカバリ (Virtual ID Recovery):** クライアントパッチによるバイナリヘッダーオフセットのズレが発生した場合、未識別ブロックに `0xFF0000XX` の仮想IDを割り当てることで、データ消失（Silent Drop）を防止します。
* **視覚的なHUDプレビュー:** ミニマップ、チャット、クイックスロットなどのUI要素の正確なアンカーとオフセットをスケーラブルなキャンバス上にレンダリングします。
* **レイアウトのクローン作成:** ワンクリックでメインキャラクターのHUD構成とチャットタブをサブキャラクターにコピーします。
* **JSONインポート/エクスポート:** 個々のキャラクターの生JSONペイロードを抽出し、他のプレイヤーとレイアウトを共有できます。

## 🛠️ ソースからのビルド
自分で実行ファイルをビルドしたい場合は、以下の手順に従ってください:

1. リポジトリのクローン:
   ```bash
   git clone https://github.com/victoriousian/AION2_HUD_Editor_V2.git
   cd AION2_HUD_Editor_V2
   ```
2. PyInstallerのインストール:
   ```bash
   pip install pyinstaller
   ```
3. ビルドスクリプトの実行 (Windows):
   ```bash
   build.bat
   ```
   *実行ファイルは `dist/` フォルダに生成されます。*

## 📖 使い方
1. `AION2_HUD_Editor.exe` を起動します。
2. ご自身の `DeviceSetting.dat` ファイルを参照して選択します。
    * *デフォルトパス: `C:\Users\{ユーザー名}\AppData\Local\AION2\Saved\PersistentDownloadDir\UserSetting\DeviceSetting.dat`*
3. **Open (Decode)** をクリックします。ツールがバイナリヘッダーとJSONペイロードを解析します。
4. パッチによりメインキャラクターのヘッダーオフセットが変更されている場合、仮想ID（例: `0xFF000000`）の下で安全に読み込まれます。ドロップダウンから選択してください。
5. **Copy Layout** ボタンを使用して、他のキャラクターに設定をクローンします。
6. **Save to DAT** をクリックします。上書きされる前に、タイムスタンプ付きの `.bak` ファイルが自動的に作成されます。

## 🤝 サポートと寄付
サブキャラクターのUI設定にかかる何時間もの無駄な作業をこのツールが救ったなら、今後のクライアントパッチに向けた継続的なメンテナンスとリバースエンジニアリング作業へのサポートをご検討ください。

🎁 **BTCウォレット:** `1JADombahDcTHR4yNywfWKtckt7zKyNHwF`

## 📝 ライセンス
MITライセンスの下で配布されています。詳細は `LICENSE` を参照してください。
