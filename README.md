# Wan2.2-Remix NSFW 14B — RunPod Serverless デプロイキット

FX-FeiHou/wan2.2-Remix の NSFW 14B を、RunPod Serverless + ComfyUI で動かすためのテンプレートです。
5B版（`wan22-remix-5b-runpod/`）から変更した点は、14BがMoEで **high / low のペアが必要** なことです。

## 10秒・開始画像＋終了画像（FLF2V）

デフォルトの `api-workflow.json` は **FLF2V（First-Last Frame to Video）** です。
Wan 2.2 には専用のFLF2Vモデルはなく、通常のI2V-A14Bエキスパートと
ComfyUI標準ノード `WanFirstLastFrameToVideo` を使います。
Gusdev06のI2Vワークフロー（`WanImageToVideo`、33フレーム）をベースに、
開始画像ノードと終了画像ノードの2枚入力に変えています。

- 解像度：720×1280（縦長）
- フレーム数：**161フレーム**（16fps × 10秒 + 1。Wanは 4n+1 フレーム）
- fps：16（`VHS_VideoCombine` の frame_rate も16）
- サンプリング：総ステップ8、ステップ3で high→low に分割、euler / simple、cfg 1、shift 2（Gusdev06と同じ）
- 呼び出し：`start_image_b64`（開始画像）と `end_image_b64`（終了画像）を
  base64で渡す。`image_b64` は開始画像の別名として使える。
  プロンプトは `prompt` / `negative_prompt` で上書きできる。
- 実行タイムアウト：デフォルト **1800秒**。10秒・161フレームは2秒・33フレームの
  約5倍の計算になるため、4090では生成だけで10分以上かかる可能性がある。
  OOMやタイムアウトが出たら、まず81フレーム（約5秒）か解像度を下げて試すこと。

注意：Gusdev06の元ワークフローに入っていた `Blink_Front_Doggystyle_I2V_HIGH`
LoRAは外してある。特定の体位専用のため、汎用の10秒FLFには不要と判断した。
使いたい場合は `LoraLoaderModelOnly` を high / low 両系統に戻すこと。

## なぜ14Bか（5Bとの違い）

- Remix NSFW 14B は fp16で約16GB、fp8で約10GBのVRAMが目安です。5Bは fp16で約8GB、fp8で約5GBでした。
- 14Bは27B total / 14B activeのMoEで、high-noise expert が前半の構図・動きを、low-noise expert が後半の質感・詳細を担当します。一度にVRAMに載るのは片方だけですが、ファイルは両方必要です。
- 公式のI2V-A14Bでは、FP8の各エキスパートが14.29GBずつ、合計28.58GBです。VAEとテキストエンコーダーを含めると14B FP8セットは約36GBになります。
- 生成は5秒クリップで、フル品質なら3〜6分、LightX2Vの4ステップLoRAを使うと1分未満になる見積もりがあります。

## 必要なファイル（5つ）

| ファイル | 置き場所 | サイズ目安 |
|---|---|---|
| Remix NSFW 14B — HIGH側（`.safetensors`） | `ComfyUI/models/diffusion_models/` | 約13〜14GB（fp8） |
| Remix NSFW 14B — LOW側（`.safetensors`） | `ComfyUI/models/diffusion_models/` | 約13〜14GB（fp8） |
| `nsfw_wan_umt5-xxl_fp8_scaled.safetensors` | `ComfyUI/models/text_encoders/` | 約6.7GB（OsriversのNSFW版UMT5。Gusdev06と同じ） |
| `wan_2.1_vae.safetensors` | `ComfyUI/models/vae/` | 0.25GB（14B用。5B用の `wan2.2_vae` と混同しないこと） |
| LightX2V 4-step LoRA（high / low、各1.23GB）※任意 | `ComfyUI/models/loras/` | 高速化したい場合のみ。Remix本体にLightningが既に組み込まれている場合は二重に載せないこと |

Remixのファイル名パターンは `wan2.2_remix_nsfw_i2v_14b_[high|low]_lighting_fp8_e4m3fn_v3.0.safetensors` です。
HFで確認済みのファイルは low側です：

`NSFW/Wan2.2_Remix_NSFW_i2v_14b_low_lighting_fp8_e4m3fn_v3.0.safetensors`

high側は同じバージョン・同じlightingで揃えてください。`high_lighting` と `low_lighting` は別バリアントなので、混ぜないこと。
※ high / low lighting が「ノイズの高低」と同じ意味かは、リポジトリのFilesタブで最終確認してください。Gusdev06のワークフローが参照する2ファイル名が正解です。

## 構成

- ベース: `runpod/worker-comfyui:5.8.4-base`（Gusdev06のDockerfileから固定）
- モデル: ビルド時に `download_models.sh` でHFから指定ファイルだけダウンロードしてイメージに焼き込む
  - リポジトリ全体は314GBあるので、丸ごとキャッシュ／ダウンロードはしないこと
  - **Gusdev06のDockerfileのダウンロードURLはそのまま使わないこと。**
    high/low両方にWan 2.1のrepackagedモデルを落とすようになっており、
    Remix NSFWの重みにならない。ファイル名だけ参考にし、ダウンロード元は
    FX-FeiHou/wan2.2-RemixのNSFWフォルダにすること（`download_models.sh` はそうなっている）
- GPU: **RTX 4090（24GB）が最低ライン**。余裕を持たせるなら L40S（48GB）/ RTX PRO 6000。
  - fp8ペアは逐次ロードでピーク約22〜24GBになるため、4090で720p・81フレームが標準的な落とし所です。
  - **10秒・161フレームは81フレームの約2倍のVRAM・時間になる。4090で720×1280が
    通らない場合は、まずL40S（48GB）で試すか、解像度・フレーム数を下げること。**
- Endpoint設定の目安:
  - Min Workers: 0
  - Max Workers: 3
  - Idle Timeout: 5秒
  - Execution Timeout: 900〜1800秒（14Bは5Bより長い。初回は1800にしておく）
  - FlashBoot: ON
  - 同時実行: 1

## 使い方

### 1. ファイル名を確認する

https://huggingface.co/FX-FeiHou/wan2.2-Remix/tree/main?not-for-all-audiences=true
を開き、`NSFW/` の中から14Bの2ファイル名をコピーする。
high側とlow側で、バージョン（v3.0）とlighting（high / low）を揃えること。

Gusdev06のワークフローも確認すること：
https://github.com/gusdev06/comfyui-wan2-2-remix-comfy-i2v-workflow
このリポジトリはRemix I2V 14B用にDocker化済みで、`api-workflow.json` が付いています。

### 2. `.env` を作る

```bash
cp .env.example .env
# MODEL_HIGH_FILE / MODEL_LOW_FILE に1.で確認したファイル名を入れる
# HF_TOKEN は、リポジトリが gated / private の場合のみ必要
```

### 3. ビルドして push する

```bash
docker build --build-arg HF_TOKEN=$HF_TOKEN -t <dockerhub-user>/wan22-remix-14b:latest .
docker push <dockerhub-user>/wan22-remix-14b:latest
```

モデルを焼き込むのでイメージは約35〜40GBになります。初回プルは時間がかかります。

### 4. Endpointを作る

RunPodコンソール → Serverless → New Endpoint → Custom Image で、
`<dockerhub-user>/wan22-remix-14b:latest` を指定する。
GPUは RTX 4090、設定は上記の目安を使う。

### 5. 呼ぶ

`test_input.json` を参考に `/run` または `/runsync` にPOSTする。
出力は動画のbase64。本番ではS3/R2に上げる改造を推奨します（`handler.py` のコメント参照）。

```bash
curl -X POST https://api.runpod.ai/v2/<endpoint-id>/run \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d @test_input.json
```

## コールドスタートの目安

- イメージ・キャッシュ済み、FlashBootスナップショットあり: 数秒〜30秒
- 普通のコールドスタート（14B、約36GBをロード）: 1〜4分
- 初回イメージプルあり: 3〜5分追加

生成自体は5秒クリップで3〜6分、LightX2V 4ステップなら1分未満が目安です。
**10秒・161フレームはその約2倍（6〜12分以上）を見込むこと。**
Execution Timeout は1800秒にしておくこと。

## 注意

- 成人のみ、フィクションのみ。実在人物のディープフェイクには使わないこと。
- `api-workflow.json` はこのキットに含めた（FLF2V・10秒版、Gusdev06ベース）。
  `handler.py` は `workflow` を渡さなければこれを自動で使う。
  開始画像はノード106（`start_image.png`）、終了画像はノード108（`end_image.png`）。
- `workflow.json` はComfyUIの画面で開くためのUI版（同じFLF2V・10秒）。
  **`api-workflow.json` は画面では読めない**ので注意。API形式をそのまま
  ドラッグ＆ドロップすると「workflow does not contain any nodes」と出る。
  画面で開きたいときは `workflow.json` をドラッグ＆ドロップすること。
  `workflow.json` は `build_workflow_ui.py` で `api-workflow.json` と
  同じノード構成から生成した。サーバーレスでは `handler.py` が
  `api-workflow.json` を優先して読むので、`workflow.json` は実行には使われない。
- このキットはテンプレート v0.3 です。GPUでの実機テストはまだしていません。まずPodでワークフローを通してからサーバーレス化してください。
- 5B版のキットは `../wan22-remix-5b-runpod/` に残してあります。コスト優先に戻したくなったらそちらを使ってください。
