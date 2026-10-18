# Microsoft Storeへの提出準備

Windows x64の買い切り版をMSIXで提出するための資材。日本の販売価格は500円。価格はMSIXではなくPartner Centerで設定する

現時点では開発者登録・名前予約・正式製品IDが未取得。検証用MSIXは提出不可。登録や契約、税・銀行情報、審査提出、販売開始をこのスクリプトは行わない

## ビルド

所有repoのrootで実行する。Pythonの依存は `requirements-build.txt`、MSIXの梱包にはWindows SDKのMakeAppx.exeが必要

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe packaging/build.py --bundle-only
.venv/Scripts/python.exe packaging/microsoft_store/build_msix.py --development
```

`--makeappx C:/.../makeappx.exe` でSDKの場所を指定できる。SDKは[Microsoftの配布](https://learn.microsoft.com/en-us/windows/apps/windows-sdk/downloads)または[Microsoft.Windows.SDK.BuildTools](https://www.nuget.org/packages/Microsoft.Windows.SDK.BuildTools)を使用する。生成先は `build/msix/` と `dist/`。`PREVIEW.msix` は検証用の架空ID・未署名であり、Storeへアップロードしない

GitHub Actionsの `Build Microsoft Store preview` は手動実行で同じ検証用MSIX・合成音の画面画像をArtifactsへ保存する。通常のGitHub Releaseとは分け、検証用MSIXをReleaseへ添付しない。正式IDやStore提出を自動化する処理は含めない

正式ID取得後は `identity.example.json` を `.local/store-identity.json` へコピーし、Partner Center「製品のID」のPackage/Identity/Name、Publisher、PublisherDisplayName、および予約した表示名を正確に設定する。CNの値をGitHub名から推測しない

```powershell
.venv/Scripts/python.exe packaging/microsoft_store/build_msix.py --identity .local/store-identity.json
```

提出用はclean checkoutのみ。元のbundleとソースが一致することを確認してからビルドする。生成するJSONにはcommit、検証用IDの有無、SHA256を記録する。署名済みや審査済みとは扱わない。clean checkoutでは同じHEADの対応ソースも生成する

Store配布MSIXは審査後にMicrosoftが署名する。直接配布のEXEの署名とは別。ローカルへのMSIX導入は署名と信頼設定が必要であり、スクリプトから証明書の登録やDeveloper Modeの変更は行わない

## 提出項目

1. [無料の個人登録入口](https://storedeveloper.microsoft.com/)から登録。本人確認は利用者が行う。公開表示名と販売者情報の表示範囲を確認し、本名や住所をrepo・画像へ記載しない
2. 製品名を予約して正式IDを取得。既存製品と衝突する場合は表示名を決め直す
3. 有料販売の受取口座・税プロファイルを設定。秘密情報はGitやチャットへ貼らない
4. 提出する版を検証・commitし、同じ版の対応ソース、依存版一覧、ライセンスをGitHubへ公開してURLを確認。公開版と異なるバイナリを旧版の対応ソースで配布しない
5. 正式IDでMSIXを再生成。Windows App Certification Kitと、署名済みMSIXのインストール・起動・PC音／マイク録音・試聴・保存・復旧・更新・アンインストールを確認する。EXE版の実機確認だけでMSIX確認済みとしない
6. `listing.ja.json` の説明・機能・キーワードを転記。カテゴリは実際の選択肢に合わせて音楽制作向けを選ぶ
7. 価格と提供状況で日本の価格を **500 JPY** に上書きし、購入者向け表示を確認。海外市場は別途決める。自動換算だけで500円と判断しない。公開時期は提出時に再確認する
8. 音声アクセスがあるためプライバシーポリシーを登録し、アプリ内からも閲覧可能にする。現行の提出画面はURLまたはポリシー本文の直接登録に対応する。本文には `PRIVACY.md` を使える。`planned_privacy_url` を使う場合は公開後の到達確認が必要
9. IARC質問票に実機能どおり回答。アプリに音源カタログ・交流・広告・決済画面はなく、利用者の音をローカル処理する。評価を自己申告で確定せず質問票の結果を使う
10. 利用許諾にGPL-3.0-onlyと同梱依存ライセンスを明示。`LICENSE` 全文と対応ソース導線を提供し、GPLで認められる再配布を制限する独自条項を足さない。Store側の契約・利用規則との整合も確認する
11. アイコン、実画面PNG、サポートURL、審査メモを登録。説明・画像が提出版と一致することを確認してから審査へ提出する

## 画像と審査用の音

アイコン原本は `icon.svg`（本repoのGPL-3.0-only）。ビルド時に44・50・150・300pxのPNGを作る

デスクトップ用スクリーンショットは1366×768以上の実画面を使用する。第三者の曲、ブラウザーの履歴、個人名・ホームパスを写さない。自作の合成音を使った波形・速度選択・再生位置・メーターの画面を用意する。画像を引き伸ばして機能や画面を偽らない

`python packaging/microsoft_store/capture_screenshots.py` は実際のQt画面に自作合成音を表示し、`dist/store-assets/` に1366×768のPNGを作る。音声処理の実機テストとは区別する。提出版の画面と日本語表示を目視確認する

英語WindowsのCIには日本語フォントがないため、画像生成時だけ[Noto Sans CJK JP](https://github.com/notofonts/noto-cjk)（SIL OFL 1.1）を固定commitから読み込む。フォントはアプリやMSIXへ同梱しない。ローカルで別のフォントを使う場合は `STORE_SCREENSHOT_FONT` にそのファイルを指定する。日本語を描画できない場合は画像生成を失敗させる

審査メモ例:

> ログイン不要。設定で「PC再生音（既定の出力 / WASAPI）」を選び、Windowsでテスト音を再生して録音してください。停止後、緑と赤の線で範囲選択、ランダム速度、再生、保存の順に確認できます。マイクはWindowsのデスクトップアプリ向けアクセス許可が必要です。保護コンテンツの録音やDRM回避機能はありません。runFullTrustはPyQt6/PortAudio/SoundCardを使う通常のWin32デスクトップ録音処理に必要で、管理者権限を要求しません。元録音の復旧キャッシュは端末内だけに保持します。

## サンプル制作での優先度

| 項目 | 判断 |
| --- | --- |
| 未保存確認・元録音復旧・保存失敗時の保護 | 販売前に優先。短い一度きりの音にも必要 |
| L/R音量・無音・入力欠落の表示 | 最小限で必要。音質修復や自動音量調整は別機能 |
| 標準48kHzで加工後WAVを出す | DAWへ持ち込むため優先。任意レートのヘッダー変更だけにしない |
| 数時間録音・録音予約 | 後回し。短い素材制作を販売対象とする |
| 0.5倍などの低速ランダム、範囲指定、逆再生 | 素材探索との相性がよい追加候補。現版には含めず需要確認後 |
| 端の短いフェード・ループ試聴・24bit/float WAV | 素材のクリック対策・DAW連携の候補。現版の保証機能に書かない |
| BPM解析・音程維持のテンポ変更 | 別の処理。現在は速度と音程を一緒に変える方式と明記 |
| 素材URL・ライセンスのメモ | 再利用元の整理に有用。自動取得や権利判定は行わない |

他人の曲を加工すれば自由に販売できる、とは説明しない。楽曲・実演・原盤等の権利は別に存在し、公開・販売時の許諾判断が必要になる。デモ素材は自作音または利用条件を確認した素材に限定する

## 一次資料（2026-10-18確認）

- [MSIX作成](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-manual-conversion)
- [Storeのパッケージ条件・署名](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/package-version-numbering)
- [市場別の価格設定](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/schedule-pricing-changes)
- [Store画像要件](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/screenshots-and-images)
- [サポート情報・プライバシーURL](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/support-info)
- [IARC](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/age-ratings?pivots=store-installer-msix)
- [Storeポリシー](https://learn.microsoft.com/windows/apps/publish/store-policies)
- [販売者契約・FOSSの責任](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/store/documents/legal/ada/fy26/MS.Store.ADAv8.10.EN.US.pdf)
- [Audacityの速度・音程変更](https://manual.audacityteam.org/man/change_speed.html)
- [文化庁の権利解説](https://www.bunka.go.jp/chosakuken/keiyaku_manual/1_1_1.html)
