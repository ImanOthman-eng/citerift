set -u
echo "clone_revision $(git rev-parse HEAD)"
echo "date $(date -u +%FT%TZ)"
echo "python $(readlink -f .venv-infer/bin/python)"
echo "index_sha256_before $(sha256sum /home/user/citerift/data/index/bench/build1/rw-2f116e9ffed718e6.sqlite | cut -d' ' -f1)"
curl -sS -m 5 https://huggingface.co >/dev/null 2>&1; echo "curl_exit_in_namespace $?"
echo "environment_variables $(env | cut -d= -f1 | sort | tr "\n" " ")"
.venv-infer/bin/citerift-rde lookup --index /home/user/citerift/data/index/bench/build1/rw-2f116e9ffed718e6.sqlite --doi 10.1038/nature16193 > /home/user/citerift/docs/verification/stage-02/ai/v2/inference/separate-process-demo/lookup-before.json; echo "lookup_before_exit $?"
for ev in ev-0003942 ev-0035101 ev-0036607; do
  .venv-infer/bin/citerift-rde ambiguity --index /home/user/citerift/data/index/bench/build1/rw-2f116e9ffed718e6.sqlite --event $ev > /home/user/citerift/docs/verification/stage-02/ai/v2/inference/separate-process-demo/$ev-ai-off.json; echo "$ev ai_off_exit $?"
  TIMEFORMAT="$ev ai_on_wall_s %R"; time .venv-infer/bin/citerift-rde ambiguity --index /home/user/citerift/data/index/bench/build1/rw-2f116e9ffed718e6.sqlite --event $ev --model-dir models/mxbai-rerank-base-v2 > /home/user/citerift/docs/verification/stage-02/ai/v2/inference/separate-process-demo/$ev-ai-on.json; echo "$ev ai_on_exit $?"
done
.venv-infer/bin/citerift-rde ambiguity --index /home/user/citerift/data/index/bench/build1/rw-2f116e9ffed718e6.sqlite --event ev-0003942 --model-dir ../empty-model-dir > /home/user/citerift/docs/verification/stage-02/ai/v2/inference/separate-process-demo/ev-0003942-no-weights.json; echo "no_weights_exit $?"
.venv-infer/bin/citerift-rde lookup --index /home/user/citerift/data/index/bench/build1/rw-2f116e9ffed718e6.sqlite --doi 10.1038/nature16193 > /home/user/citerift/docs/verification/stage-02/ai/v2/inference/separate-process-demo/lookup-after.json; echo "lookup_after_exit $?"
echo "index_sha256_after $(sha256sum /home/user/citerift/data/index/bench/build1/rw-2f116e9ffed718e6.sqlite | cut -d' ' -f1)"
