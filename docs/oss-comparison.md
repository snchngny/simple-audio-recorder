# 類似OSSと改善候補

調査日: 2026-10-18。公式README・マニュアル・ライセンスを比較。他OSSのコード移植や実機比較は行っていない

## 現状

main.pyのQt画面に録音・試聴・トリミング・WAV保存を集約。設定はQSettings、録音はsounddevice、保存はSciPy、波形はpyqtgraph
外部API・DB・音声アップロード処理はない。録音全体をメモリに保持するため長時間録音や異常終了からの復旧には向かない

## 比較

| OSS / 一次資料 | 参考にする点 | 判断 |
| --- | --- | --- |
| [Audacity](https://github.com/audacity/audacity) / [録音ガイド](https://support.audacityteam.org/basics/recording-your-voice-and-microphone) | 入力選択、デバイス再検索、モノラル選択、レベル・クリッピング表示 | 操作順とレベル表示を参考にする。多機能編集全体の移植は保守負担が大きい |
| [Tenacity](https://github.com/tenacityteam/tenacity) / [公式docs](https://tenacityaudio.org/docs/) | 録音・編集・複数形式。GPL-2.0-or-later。GitHubはミラー、開発先はCodeberg | 本格編集が必要なら既存アプリを優先。GitHubだけで開発停止と判断しない |
| [AudioMass](https://github.com/pkalogiros/AudioMass) / [MIT](https://github.com/pkalogiros/AudioMass/blob/production/LICENSE) | ブラウザで波形の範囲選択から試聴・編集へ進む操作 | デスクトップの入力API・権限とは異なる。ブラウザへの作り直しは対象外 |
| [sounddeviceの録音例](https://python-sounddevice.readthedocs.io/en/latest/examples.html) | callback→queue→別処理でファイルへ保存 | 長時間録音では新しいエンジンより既存依存の活用を優先 |

Audacityのライセンスは対象版で確認。古いマニュアルのGPLv2記載を現在の全配布物へ当てはめない。コードを取り込む場合は対象ファイルと版の条件を確認する

## 優先度

| 優先 | 改善 | 期待効果・注意点 | 確認方法 |
| --- | --- | --- | --- |
| 今回対応 | デバイス既定レートを採用し開始前に検証 | 44.1kHz非対応デバイスの失敗を減らす | 48kHz mockと実機stream |
| 今回対応 | device indexを保持、API名を表示 | 同名デバイスの混同を減らす | 重複デバイスのテスト |
| 今回対応 | 終了・開始失敗時にstreamをclose | デバイス占有の残留を防ぐ | lifecycleテスト |
| 今回対応 | Win/Macインストーラー、依存固定、CI、ライセンス | 手動配布を減らす | OS別ビルドと起動 |
| 次候補 | レベル・クリッピング・入力overflow表示 | 無音や歪みを録音中に把握。callbackでUI更新しない | 既知振幅とoverflow注入 |
| 次候補 | 未保存録音を新規録音・終了から保護 | 誤操作による消失を減らす | 終了・再録音・キャンセル |
| 次候補 | 一時WAVへ順次保存、波形だけ短時間保持 | メモリ増加と異常終了時の消失を抑える。容量・復旧処理が必要 | 長時間、容量不足、復旧 |
| 次候補 | 接続変更時の再検索、名前とAPIで設定保存 | USB再接続のindex変化に対応。名前重複に注意 | 再接続と消失 |
| 後続 | 速度数値入力、undo、フェード | 短い素材の編集改善。音程維持は別DSPが必要 | 操作受入と既知信号 |
| 配布拡大時 | Windows署名・Mac Developer ID署名と公証 | 初回起動制限を減らす。証明書設定が必要 | クリーン実機への導入 |

短い音を確実に録音・保存する用途を優先。多トラック・エフェクト・多数形式が必要ならAudacity等の併用で変更を抑えられる

## 対応の根拠

- [sounddevice公式](https://python-sounddevice.readthedocs.io/en/latest/installation.html): Windows/Macのpip版はPortAudio同梱
- [PyInstaller公式](https://pyinstaller.org/en/stable/usage.html): 各OSでbundle化
- [GitHubランナー](https://docs.github.com/en/actions/reference/runners/github-hosted-runners): Win x64・Mac arm64・Mac Intel
- [Inno Setup](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm): PrivilegesRequired=lowestで利用者単位のインストール
- [PyQt公式](https://en.riverbankcomputing.com/software/pyqt): GPLv3と商用の選択制。今回はGPL-3.0-only

ビルド成功は実機録音・再生成功を保証しない。公開版の受入ではOS権限・USB機器・保存先を確認する
