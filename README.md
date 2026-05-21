# simple-audio-recorder

Pythonで作ったシンプルなmacOS用オーディオ録音アプリです。

## 開発

仮想環境を作り、依存パッケージを入れてから起動します。

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## バージョン管理

アプリのバージョンは `VERSION` ファイルで管理します。

```text
0.1.0
```

ビルドすると、この値がmacOSアプリの `Info.plist` に入ります。

```text
CFBundleShortVersionString = ユーザーに見えるバージョン
CFBundleVersion = 内部ビルド番号
```

内部ビルド番号は、通常はGitのコミット数から自動で入ります。手動で指定したい場合は `BUILD_NUMBER` を付けて実行します。

```bash
BUILD_NUMBER=12 ./build_app.sh
```

## macOSアプリのビルド

```bash
./build_app.sh
```

成功すると、次の2つが作られます。

```text
dist/SimpleAudioRecorder.app
dist/SimpleAudioRecorder-v0.1.0-mac.zip
```

`.app` はローカル確認用、`.zip` はGitHub Releaseに添付する配布用です。

## リリース手順

1. `VERSION` を次のバージョンに更新する。
2. 必要な変更をコミットする。
3. `./build_app.sh` で配布zipを作る。
4. Gitタグを作ってpushする。

```bash
git tag v0.1.0
git push origin v0.1.0
```

5. GitHubのReleasesで `v0.1.0` のリリースを作り、`dist/SimpleAudioRecorder-v0.1.0-mac.zip` を添付する。

## 署名について

現在のビルドはローカル配布向けの簡易署名です。自分のMacでは使いやすいですが、他の人へ広く配る場合はApple Developer IDで署名し、notarizationを行うのが正式な配布方法です。
