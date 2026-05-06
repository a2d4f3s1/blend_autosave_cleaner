# Blend Autosave Cleaner

Blender の Temp フォルダに溜まる自動保存 `.blend` 系ファイルを、保持日数経過後に自動削除する Extension です。
削除は既定で OS のごみ箱送りなので、誤削除しても復元できます。

## 【導入方法】

1. リリースから `blend_autosave_cleaner_X.Y.Z(YYMMDD).zip` を取得
2. Blender 4.2 以降を起動
3. **Edit > Preferences > Get Extensions > 右上の `▼` > Install from Disk** から zip を指定
4. **Add-ons** タブで `Blend Autosave Cleaner` を有効化

## 【設定項目】

Preferences で以下を調整できます。

### 削除対象（Targets）

| 項目 | 既定値 | 説明 |
|---|---|---|
| Target `.blend` | ON | autosave 形式の `.blend` を対象に |
| Target `.blend1` | ON | バックアップ `.blend1` を対象に |
| Target `.blend2` | ON | バックアップ `.blend2` を対象に |
| Target `quit.blend` | ON | 終了時セーブを対象に |

### 動作（Behavior）

| 項目 | 既定値 | 説明 |
|---|---|---|
| Retention Days（保持日数） | `7` | この日数より古いファイルを削除（`0` で無効化） |
| Send to Recycle Bin（ごみ箱に送る） | ON | OS のごみ箱に送る（OFF で完全削除） |
| Run on Blender startup（起動時に実行） | ON | Blender 起動時に自動実行 |
| Confirm before deletion（削除前に確認） | OFF | 削除前にダイアログを表示 |
| Dry Run（ドライラン） | **ON** | 削除せずログのみ記録（**初回安全のため既定 ON**。本削除するには OFF へ）|
| Enable log file（ログを有効化） | ON | 実行ログを `<temp>/blend_autosave_cleaner.log` に追記（直近100行のみ保持） |

## 【使用方法】

- **自動**: Blender 起動時に自動実行されます（既定 ON）
- **手動**: Preferences の `Clean Now` ボタンで即時実行
- **Tempフォルダを開く**: `Open Temp Folder` ボタンで対象フォルダを開きます

> ⚠️ **インストール直後は `Dry Run` が ON になっています**。意図せずファイルが消えないようにするための初期設定です。本削除するには Preferences で `Dry Run` を OFF にしてください。

### 初回利用時の推奨手順

1. インストール直後の状態（`Dry Run` ON）のまま `Clean Now` を実行
2. ステータスバーの結果（`Deleted N file(s) (X MB), dry run`）と `<temp>/blend_autosave_cleaner.log` で対象を確認
3. 問題なければ `Dry Run` を **OFF** に切り替えて本実行

## 【削除対象】

- **場所**: `Edit > Preferences > File Paths > Temporary Files` で指定したフォルダ（未設定時は OS の Temp フォルダ）
- **対象ファイル種別**: `*.blend` / `*.blend1` / `*.blend2` / `quit.blend`（個別 ON/OFF 可能）
- **判定基準**: ファイルの最終更新日時（mtime）が `現在時刻 - Retention Days` より古いもの
- **削除先**: ごみ箱（既定）または完全削除（Preferences で切替可能）
- **再帰**: しません。Temp フォルダ直下のみ。

## 【対応環境】

- Blender 4.2 以降
- Windows / macOS / Linux

## 【ライセンス】

- 本体: **GPL-2.0-or-later** （`LICENSE` 全文同梱）
- 含まれる外部ライブラリ:
  - [Send2Trash 2.1.0](https://github.com/arsenetar/send2trash) — BSD-3-Clause / Copyright (c) 2017, Virgil Dupras  
    ライセンス全文: [`LICENSES/Send2Trash-LICENSE`](LICENSES/Send2Trash-LICENSE)

## 【更新履歴】

#### [1.0.0] (2026-05)
- 初回リリース
