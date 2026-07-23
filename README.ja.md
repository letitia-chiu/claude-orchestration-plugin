# orchestration — Claude Code のための「統率と委任」ワークフロー

[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · **日本語**

シンプルなアイデアをパッケージ化した、プロジェクト横断のスラッシュコマンドとサブエージェントのセットです。**メインセッションは最もコストの高いトークンなのだから、「考えること」だけに専念すべきである——計画を立て、作業を分解し、検証し、引き継ぐ。機械的な偵察・実装・力仕事は、モデルを固定した3つのサブエージェントに任せる。** これをどのプロジェクトにインストールしても、メインセッションは単純作業をしなくなります。

> 🌐 **あなたの言語で動きます。** コマンドとサブエージェントはメンテナンス性のために英語で書かれていますが、そのすべてに「あなたの言語をミラーリングせよ」という指示が組み込まれています。日本語でチャットすれば、Claude は日本語で計画を立て、質問し、報告します。繁体字中国語でチャットすれば、繁体字中国語で答えます。内部を英語化することは、アシスタントを英語専用にすることを**意味しません**。

## インストール

プラグインマーケットプレイスから（公開リポジトリ）:

```
/plugin marketplace add letitia-chiu/claude-orchestration-plugin
/plugin install orchestration@orchestration-marketplace
```

マーケットプレイスを介さずに開発中に試す場合:

```
claude --plugin-dir /path/to/claude-orchestration-plugin
```

インストール後、コマンドはプラグイン名で名前空間化されて表示されます: `/orchestration:kickoff`、`/orchestration:go`、`/orchestration:dispatch`、`/orchestration:wrapup`、`/orchestration:init-playbook`。

## 三層アーキテクチャ

```
Orchestrator（メインセッション — 利用可能な最強のモデル + 高いエフォート）
│  やることは限定的: リクエストの理解、盲点/質問の洗い出し、作業の分解、
│  ディスパッチ、敵対的検証、統合、引き継ぎ。
│
├─ scout    = Haiku 4.5   読み取り専用の偵察（ファイルを探す／コードを読む／
│                          現状を要約する — 結論のみ返す。ツールは
│                          Read/Glob/Grep にロックされている）
├─ worker   = Sonnet 5    デフォルトの実行担当（仕様が明確な実装／テスト／
│                          一括編集／ドキュメント）
└─ executor = Opus 4.8    難しい実行担当（既に仕様化された大規模リファクタリング／
                          精密な編集 — 1行目で自分のモデルIDを自己申告するので、
                          誤って違う階層を動かしていることに気づかず進む心配がない）
```

5つのスラッシュコマンドが、ワークフローの各段階に対応しています。

| コマンド | 内容 |
|---|---|
| `/orchestration:kickoff` | 開始儀式: 盲点の洗い出し → 質問 → 計画（ディスパッチの分割方法を含む）——**計画で停止し、実行は開始しない** |
| `/orchestration:go` | 実行指示: まず authoritative plan の同一性（planning branch／plan commit SHA／canonical base）を検証し、一度に1つの role または batch のみを許可する——会話の記憶だけでは実行権限にならない |
| `/orchestration:dispatch` | タスクを完全な task packet に変換し、workflow role を判定したうえで、`agent-routing.json` に従って Claude subagent 階層または bounded external runner にルーティングする |
| `/orchestration:wrapup` | 締めの儀式: 検証バッテリー → 既知の失敗チェック → provider／session／artifact の証跡 → 引き継ぎ |
| `/orchestration:init-playbook` | 対象プロジェクトに `docs/playbook/` の骨格を生成する——`agent-routing.json` を含む11ファイル（既存ファイルは上書きしない。埋め込みテンプレートは自動テストでドリフトから保護される） |

各階層の背後にあるコスト感覚（API価格の比率であり、サブスクリプションのクォータもほぼ同じ傾向）: **Haiku : Sonnet : Opus ≈ 1 : 3 : 15。** orchestrator が使うトークン1つ1つがシステム内で最もコストの高いトークンです——だからこそ、生の読み取りや機械的な編集は下位に委任し、判断だけを自分の手元に残します。

## Role-first プロバイダールーティング（0.6.0）

0.6.0 以降、ワークフローは**タスクが何であるか**（workflow role）と**どのエンジンが実行するか**（provider/profile）を分離します。ルーティングの SSOT は対象プロジェクトの `docs/playbook/agent-routing.json` です。プロバイダーの切り替えはルーティングファイル＋task packet の変更だけで済み、コマンド群や方法論を書き直す必要はありません。

```text
role             ＝ 仕事の職責（振る舞いの契約）
provider/profile ＝ 実行エンジンと権限の境界
```

**権限は制御ウィンドウに残ります。** ChatGPT／ユーザー制御ウィンドウが architecture、authoritative planning、authorization、acceptance、finding adjudication、final ratification を保持します。実行プロバイダーは明示的に許可された task packet を実行するだけであり、plan や acceptance のオーナーには決してなりません。

新規プロジェクトに生成されるデフォルトルーティング:

```text
feasibility_verifier -> codex_cli / codex_read_only
implementer          -> codex_cli / codex_workspace_write
adversarial_reviewer -> claude_cli / claude_read_only
```

サポートされる provider kind は `claude_subagent`、`codex_cli`、`claude_cli` の3種類のみです。任意プロバイダーのサポート、動的な provider discovery、capability negotiation、automatic fallback、プロバイダー間の session migration はありません。

**Claude の三層は `claude_subagent` パスとして完全に残ります。** `scout`、`worker`、`executor` は変更なく完全にサポートされます——これらはルーティング上の fallback であり（`implementer` を worker/executor に戻すのは1行のルーティング変更です）、削除された旧機能でも、永久に固定された implementer でもありません。

**Bounded external-agent runner。** 外部 CLI プロバイダーは必ず `scripts/orchestration_agent.py` という限定的な process-safety wrapper 経由で呼び出されます。提供機能: routing と provider/profile の検証、単一 role のプロセス起動、wall-clock timeout と interrupt の分類、stdout／stderr の分離保存、共有スキーマ（`examples/schemas/orchestration-result.schema.json`）による structured result の検証、pre/post Git 証跡、読み取り専用ロールの mutation 検出、implementation changed-path allowlist 検証、artifact の SHA-256 manifest、fail-closed な結果分類。これは自動で計画したり、次のロールに連鎖したり、retry／fallback したり、commit／push／PR／merge したり、違反変更をクリーンアップしたり**しません**——generic provider SDK でも、Xinghui Runtime の provider adapter でもありません。

**Git と副作用の境界。** 実行許可は Git 許可ではありません: commit、push、PR、merge はそれぞれ個別の明示的な許可が必要です。実際の外部 CLI 呼び出しには task packet に `External-side-effect authorization: ALLOW_PROVIDER_INVOCATION` が必要です。implementer は reviewer を dispatch できません。reviewer は読み取り専用でコードを修復できません。reviewer の findings は制御ウィンドウが裁定するまで candidate findings にすぎません。task packet テンプレートは `examples/task-packets/` にあります。

**Real-CLI の現状。** 自動テストは偽（fake）の Codex／Claude 実行ファイルを使用します。本番の implementation Gate でこのワークフローを使う前に、別途許可された real-CLI smoke test が依然として必要です——実際の network isolation、schema／stream 互換性、quota／timeout の挙動は未検証です。本リリースは開発用 orchestration plugin を適応させるものであり、将来の Xinghui Runtime Claude/Codex adapter を実装するものではありません。

## 階層ごとのモデルをカスタマイズ（更新に強い）

各階層は既定値を固定して出荷されます: `scout` = `claude-haiku-4-5-20251001`、`worker` = `claude-sonnet-5`、`executor` = `claude-opus-4-8`。これは妥当な出発点であって、固定ではありません。

ある階層を別のモデルで動かしたいとき、**plugin の `agents/*.md` を編集しないでください**——plugin を更新すると上書きされ、変更は失われます。Claude Code の `settings.json` にも「エージェントごとのモデル指定」スイッチはありません。唯一の更新に強い仕組みが**同名シャドーイング（agent shadowing）**です: 自分の scope に同じ `name:` のサブエージェントを置くと plugin 版を丸ごと置き換え、しかも更新が決して触れない場所に存在します。優先順位は高い順に: プロジェクト `.claude/agents/` → ユーザー `~/.claude/agents/` → plugin。

そのままコピーして使える override は [`examples/agents/`](examples/agents/) にあります——変えたい階層をコピーし、`model:` の行だけ編集します:

```
# どこでも適用（ユーザー scope）……
cp examples/agents/executor.md ~/.claude/agents/executor.md
# ……または特定プロジェクトのみ（プロジェクト scope）
cp examples/agents/worker.md   .claude/agents/worker.md
# あとはファイルを開いて `model:` の行を変更
```

注意点は2つ、いずれも範例ファイル冒頭のコメントにも記載しています:

- override は **plugin のエージェントを丸ごと置き換えます**（本体も含む）。したがって plugin 側のエージェント指示の改善はこのコピーには届きません——必要なら手動で再同期してください。
- `executor` には「起動時にモデル ID を自己申告し、不一致なら停止する」フィンガープリント探針が入っています。`model:` を変えたら本体の対応する model ID も合わせて変更しないと、自身のチェックで停止します。

一時的に**全階層**を一つのモデルへ一括で寄せたい場合（階層別ではなく）は、環境変数 `CLAUDE_CODE_SUBAGENT_MODEL` で全サブエージェントを一度に上書きできます。

## エンジンであって、ドメイン知識ではない

このプラグインが提供するのは**エンジン**です: 役割分担（scout/worker/executor——そのモデルの固定と責任範囲）、ワークフロー（kickoff / dispatch / wrap-up の各儀式）、そして脱プロジェクト化・汎用化された1本の `orchestration.md` 方法論です。

意図的に提供**しない**のは、あなたのプロジェクト固有のドメイン知識です: 特定のコードベースの鉄則、これまでにぶつかった落とし穴、検証バッテリーの詳細、独自の引き継ぎ規約。これらはプロジェクトが自ら育てていくべきものであり、プラグインに焼き込んでしまえば、次のプロジェクトでは邪魔になる古びた前提になるだけです。

そのドメイン知識のための入口が `/orchestration:init-playbook` です。対象プロジェクトに空の `docs/playbook/` 骨格を生成します（汎用の `orchestration.md`、普遍的なエンジニアリング教訓を初期シードとした `known-failures.md` の出発点、記入欄を備えたテンプレートファイルを含みます）。そのプロジェクトは、自身の開発を通じて一件ずつそこに書き込んでいきます。エンジンはどこにでもインストールできますが、ドメイン知識は自分自身のプロジェクトの中でしか育ちません。

## License

[MIT](LICENSE) © 2026 letitia-chiu
