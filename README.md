# Simple Audio Recorder

Windows・macOS向けの小さな録音アプリ。入力をL/Rへ割り当て、波形で範囲を選び、試聴して16bitステレオWAVへ保存する

## インストール

[Releases](https://github.com/snchngny/simple-audio-recorder/releases)から自分の環境用を選ぶ

| 環境 | 配布ファイル | 導入方法 |
| --- | --- | --- |
| Windows 10/11 x64 | `*-windows-x64-setup.exe` | 実行してインストール。管理者権限不要 |
| Mac Apple Silicon | `*-macos-arm64.dmg` | 開いてアプリをApplicationsへドラッグ |
| Mac Intel | `*-macos-x86_64.dmg` | 開いてアプリをApplicationsへドラッグ |

Macの対応OSは同梱Qtの要件にも依存する。まずmacOS 15のActions環境で起動を検証する。Windows ARMネイティブ版は未対応

Windowsの発行元署名、MacのDeveloper ID署名・Apple公証は未設定。OSが警告・起動制限を表示する場合がある。Macの簡易署名は公証の代替ではない
初回ビルドはActionsのArtifacts、タグ付きビルドは下書きReleaseに保存する

## 使い方

1. 「設定」で入力デバイスとL/Rチャンネル、保存先を選ぶ
2. 「録音」を押し、終わったら「録音停止」
3. 緑・赤の線で保存する範囲を選び、「再生」で確認
4. 「保存」でWAVを書き出す

再生中は黒い縦線が現在位置を示す。選択範囲の先頭から再生速度に合わせて進み、停止時は非表示になる

モノラル入力は左右へ同じ音を配置。録音レートはデバイスの既定値を使用。同名デバイスはMME・DirectSound・WASAPI等のAPI名で区別できる
ランダム速度は再生速度と音程を一緒に変える。元録音は保持し、試聴と保存時に加工済み音声を48kHzへ変換する。保存は16bitステレオWAV。音程を維持するテンポ変更ではない

マイクが使えない場合:

- Windows：「設定 → プライバシーとセキュリティ → マイク」でマイクとデスクトップアプリのアクセスを確認
- Mac：「システム設定 → プライバシーとセキュリティ → マイク」でアプリを許可
- 入力デバイスとL/R割当を確認
- WindowsでPC再生音を録る場合は、入力デバイスで「PC再生音（既定の出力 / WASAPI）」を選ぶ。ドライバー追加は不要。録音開始時のWindows既定再生デバイスを48kHzで録音する。Macは仮想入力等が別途必要

短いサンプル素材の制作向け。入力のL/Rピークと音割れの可能性を表示する。音割れを自動修復する機能ではない

元録音は端末内の復旧キャッシュへ逐次書き込み、描画用には直近約5秒を保持する。前回異常終了時は起動後に復旧を選べる。復旧するのは元録音で、トリミング位置や速度は選び直す
録り直し・終了時には未保存のサンプルを確認する。「保存」は現在の選択範囲と速度のWAVを書き出す。元録音も必要なら先に全範囲・1.0倍で別名保存する
キャッシュは `QStandardPaths.AppLocalDataLocation` 下の `recovery/` に保存し、正常終了または明示した破棄で削除する。録音を外部送信しない。ディスク故障・電源断・アンインストールからの復旧は保証しない

録音中のメモリ増加は抑えているが、加工・試聴・WAV書出しは選択範囲をメモリへ展開する。数時間の選択範囲の加工や4GB超のWAVは販売対象として検証していない。サンプル用途では必要な短い区間を選ぶ

## 開発

Python 3.12を使用。依存を `.venv` に入れる

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-build.txt
.venv/Scripts/python main.py
.venv/Scripts/python -m pytest -q
```

Mac:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
python main.py
python -m pytest -q
```

## インストーラーの作成

各OS上で `python packaging/build.py` を実行。別OS用のクロスビルドは行わない
Windowsでは[Inno Setup 6](https://jrsoftware.org/isinfo.php)が必要
本体だけ確認する場合は `python packaging/build.py --bundle-only`
生成先はrepo内の `build/` と `dist/`。両方Git管理外。依存版一覧・ライセンス本文を自動同梱する

`.github/workflows/build.yml` はmainへのpush・PR・手動実行で、Windows x64、Mac arm64、Mac Intelのテスト・ビルド・起動確認を行う
起動確認はQtとPortAudioのロードまで。実機の録音・再生やOS権限は別途確認が必要

リリース時は `VERSION` を更新してcommitし、その版と一致するタグをpushする

```bash
git tag v0.3.1
git push origin main
git push origin v0.3.1
```

全OS成功後、インストーラー・対応ソース・依存版一覧・ライセンス・SHA256を同じタグの下書きReleaseへ添付
実機で録音・再生・保存を確認後に公開する。タグは既存リリースを上書きしない

従来の `build_app.sh` と `run_recorder.command` は旧Mac環境向け。新しい配布処理の入口は `packaging/build.py`

## ライセンス

本アプリのコードは [GPL-3.0-only](LICENSE)。商用利用・販売も可能だが、改変版やバイナリを配布する場合はGPLの条件に従い対応ソースも提供する
依存ライブラリは各ライセンスに従う。[利用ライブラリ](THIRD_PARTY_NOTICES.md)を参照

類似OSSの比較・改善候補は[調査メモ](docs/oss-comparison.md)を参照
