#!/bin/bash
#SBATCH --job-name=gpt_eval_4a16_llama3.1_8b:8b
#SBATCH --partition=gpu-preempt
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:a16:8
#SBATCH --cpus-per-task=36
#SBATCH --mem=256G
#SBATCH --time=48:00:00
#SBATCH --output=gpt_eval_llama3.1_8b_%j.out
#SBATCH --error=gpt_eval_llama3.1_8b_%j.err

# ================================================================
# 4-GPU V100 Evaluation (Single Node)
# Expected time: ~10 hours for 39,799 GPTs
# ================================================================

echo "========================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Starting at: $(date)"
echo "========================================"

nvidia-smi

# ================================================================
# Setup Paths
# ================================================================
PI_ACCT=$(sacctmgr show user $USER format=DefaultAccount%40 -n | tr -d '+' | xargs)

export OLLAMA_CONTAINER="/work/${PI_ACCT}/${USER}/workspace/ollama/ollama_latest.sif"
# export OLLAMA_MODELS="/work/pi_phuc_umass_edu/vdle_umass_edu/workspace/ollama/models"
export OLLAMA_MODELS="$HOME/.ollama/models"
export WORK_DIR="/work/${PI_ACCT}/${USER}/workspace/GPTracker"
export MODEL="llama3.1:8b"
NUM_GPUS=8
# export MODEL="qwen2.5:7b-instruct"

cd $WORK_DIR
echo "Working directory: $(pwd)"
echo "Ollama container: $OLLAMA_CONTAINER"
echo "Ollama models: $OLLAMA_MODELS"

# Load modules
module load apptainer/latest
module  load cuda/12.1
# module load cuda/12.1
# module load python/3.9

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install "numpy<2.0" pandas requests tqdm --user --quiet

# ================================================================
# Start Ollama Servers on All 4 GPUs
# ================================================================


BASE_PORT=11434

echo ""
echo "========================================"
echo "Starting $NUM_GPUS Ollama Servers"
echo "========================================"

# Array to store PIDs
declare -a OLLAMA_PIDS

for gpu_id in $(seq 0 $((NUM_GPUS - 1))); do
    port=$((BASE_PORT + gpu_id))
    
    echo "Starting Ollama on GPU $gpu_id (port $port)..."
    
    CUDA_VISIBLE_DEVICES=$gpu_id \
    apptainer exec --nv \
        --bind $OLLAMA_MODELS:/root/.ollama/models \
        --env OLLAMA_HOST=127.0.0.1:$port \
        $OLLAMA_CONTAINER \
        ollama serve > ollama_gpu${gpu_id}_${MODEL}.log 2>&1 &
    
    OLLAMA_PIDS[$gpu_id]=$!
    echo "  PID: ${OLLAMA_PIDS[$gpu_id]}"
    
    sleep 5
done

echo ""
echo "Waiting for Ollama servers to initialize..."
sleep 10



echo ""
echo "========================================"
echo "Testing Ollama Servers with $MODEL"
echo "========================================"

ALL_READY=true

for gpu_id in $(seq 0 $((NUM_GPUS - 1))); do
    port=$((BASE_PORT + gpu_id))
    
    echo "Testing GPU $gpu_id (port $port)..."
    
    # Send test request
    RESPONSE=$(curl -s -X POST http://127.0.0.1:$port/api/generate -d "{
      \"model\": \"$MODEL\",
      \"prompt\": \"Hi\",
      \"stream\": false
    }" 2>&1)
    
    # Check if request succeeded
    if echo "$RESPONSE" | grep -q "\"response\""; then
        echo "  ✅ GPU $gpu_id responding correctly"
    else
        echo "  ❌ GPU $gpu_id FAILED to respond!"
        echo "     Error: $RESPONSE"
        cat ollama_gpu${gpu_id}_${MODEL}.log
        ALL_READY=false
    fi
done

if [ "$ALL_READY" = false ]; then
    echo ""
    echo "❌ Some Ollama servers failed. Exiting."
    for pid in "${OLLAMA_PIDS[@]}"; do
        kill $pid 2>/dev/null
    done
    exit 1
fi

echo ""
echo "✅ All $NUM_GPUS servers ready!"
echo ""

# ================================================================
# Verify All Ollama Servers
# ================================================================

echo ""
echo "========================================"
echo "Verifying Ollama Servers"
echo "========================================"

ALL_READY=true

for gpu_id in $(seq 0 $((NUM_GPUS - 1))); do
    port=$((BASE_PORT + gpu_id))
    
    if curl -s http://127.0.0.1:$port/api/tags > /dev/null; then
        echo "  ✅ GPU $gpu_id (port $port) is ready"
    else
        echo "  ❌ GPU $gpu_id (port $port) FAILED!"
        cat ollama_gpu${gpu_id}.log
        ALL_READY=false
    fi
done

if [ "$ALL_READY" = false ]; then
    echo ""
    echo "❌ Some Ollama servers failed to start. Exiting."
    # Kill all Ollama processes
    for pid in "${OLLAMA_PIDS[@]}"; do
        kill $pid 2>/dev/null
    done
    exit 1
fi

# ================================================================
# Activate Python Environment
# ================================================================

echo ""
echo "Activating Python environment..."
source /work/${PI_ACCT}/${USER}/anaconda/bin/activate py39
# Or: conda activate py39

python --version
which python

# ================================================================
# Start Python Workers
# ================================================================

echo ""
echo "========================================"
echo "Starting $NUM_GPUS Python Workers"
echo "========================================"
echo "Each worker processes ~9,950 GPTs"
echo "Expected time: ~10 hours"
echo ""

# Array to store worker PIDs
declare -a WORKER_PIDS

for worker_id in $(seq 0 $((NUM_GPUS - 1))); do
    port=$((BASE_PORT + worker_id))
    
    echo "Starting Worker $worker_id (GPU $worker_id, port $port)..."
    
    python run_with_ollama_multi_gpu_resume.py \
        --input_file data/all_2025-11-18-final.json \
        --worker_id $worker_id \
        --num_workers $NUM_GPUS \
        --ollama_port $port \
	--model $MODEL > worker${worker_id}_${MODEL}.log 2>&1 &
    
    WORKER_PIDS[$worker_id]=$!
    echo "  Worker $worker_id PID: ${WORKER_PIDS[$worker_id]}"
done

echo ""
echo "========================================"
echo "✅ All $NUM_GPUS workers started!"
echo "========================================"
echo ""

# ================================================================
# Wait for All Workers to Complete
# ================================================================

echo "Waiting for workers to complete..."
echo "(This will take approximately 10 hours)"
echo ""

# Wait for each worker
for worker_id in $(seq 0 $((NUM_GPUS - 1))); do
    wait ${WORKER_PIDS[$worker_id]}
    EXIT_CODE=$?
    echo "Worker $worker_id finished with exit code: $EXIT_CODE"
done

# ================================================================
# Cleanup
# ================================================================

echo ""
echo "Stopping all Ollama servers..."
for pid in "${OLLAMA_PIDS[@]}"; do
    kill $pid 2>/dev/null
done
sleep 2

echo ""
echo "========================================"
echo "Job Complete at: $(date)"
echo "========================================"
