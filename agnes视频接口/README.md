# Agnes 视频接口

这个目录用于调用 Agnes AI 的图生视频接口。官方接口是异步任务：

- 创建任务：`POST https://apihub.agnes-ai.com/v1/videos`
- 查询任务：`GET https://apihub.agnes-ai.com/v1/videos/{task_id}`

官方文档说明：`image` 参数需要图片 URL，不支持直接传本地图片路径。使用本地首帧前，需要先把图片上传到可访问的 URL。

## 配置 Key

PowerShell 临时配置：

```powershell
$env:AGNES_API_KEY="你的 Agnes API Key"
```

也可以在命令里传：

```powershell
-ApiKey "你的 Agnes API Key"
```

## 图生视频

```powershell
powershell -ExecutionPolicy Bypass -File .\agnes_video_client.ps1 create `
  -Prompt "A felt stop-motion plush elephant drum creature rolls sideways through the arena, low camera, no text." `
  -ImageUrl "https://example.com/scene_002_b_first.png" `
  -NumFrames 121 `
  -Width 1152 `
  -Height 768 `
  -FrameRate 24
```

返回里会有任务 ID，通常是 `id`。

## 查询任务

```powershell
powershell -ExecutionPolicy Bypass -File .\agnes_video_client.ps1 get -TaskId "task_xxxxx"
```

## 轮询任务

```powershell
powershell -ExecutionPolicy Bypass -File .\agnes_video_client.ps1 poll -TaskId "task_xxxxx" -PollIntervalSeconds 10
```

## 下载成片

```powershell
powershell -ExecutionPolicy Bypass -File .\agnes_video_client.ps1 download -TaskId "task_xxxxx" -Output "output/scene_002_b.mp4"
```

## 干跑检查请求

```powershell
powershell -ExecutionPolicy Bypass -File .\agnes_video_client.ps1 create `
  -Prompt "test" `
  -ImageUrl "https://example.com/input.png" `
  -DryRun
```

## 参数提示

- 默认模型按官方文档使用 `agnes-video-v1.2`。
- 如果你的 Agnes 账号后台已开放新模型，可以加 `-Model "agnes-video-v2.0"`。
- `NumFrames` 必须满足 `8n + 1`，例如 `81`、`121`、`161`、`241`、`441`。
- `NumFrames` 最大值为 `441`。
- `ImageUrl` 是单首帧图生视频。
- `Images` 可传多张 URL，用于多图视频或关键帧模式。
- `Mode keyframes` 会把 `Images` 放进 `extra_body.image`，并设置 `extra_body.mode = keyframes`。
