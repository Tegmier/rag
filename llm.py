from torch import cuda, bfloat16
import torch
import transformers

model_id = 'meta-llama/Llama-2-7b-chat-hf'
# torch.cuda.set_device(0)

device = f'cuda:{cuda.current_device()}' if cuda.is_available() else 'cpu'

print(torch.cuda.get_device_properties(cuda.current_device()))

# set quantization configuration to load large model with less GPU memory
# this requires the `bitsandbytes` library
bnb_config = transformers.BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type='nf4',
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=bfloat16
    # bnb_4bit_compute_dtype=torch.float16
)

# begin initializing HF items, you need an access token
hf_auth = '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'
model_config = transformers.AutoConfig.from_pretrained(
    model_id,
    token=hf_auth
)
                                
model = transformers.AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    config=model_config,
    quantization_config=bnb_config,
    device_map='cuda:0',
    token=hf_auth
)

# enable evaluation mode to allow model inference
model.eval()

print(f"Model loaded on {device}")

tokenizer = transformers.AutoTokenizer.from_pretrained(
    model_id,
    token=hf_auth
)

stop_list = ['\nHuman:', '\n```\n']

stop_token_ids = [tokenizer(x)['input_ids'] for x in stop_list]

stop_token_ids = [torch.LongTensor(x).to(device) for x in stop_token_ids]

from transformers import StoppingCriteria, StoppingCriteriaList

# define custom stopping criteria object
class StopOnTokens(StoppingCriteria):
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        for stop_ids in stop_token_ids:
            if torch.eq(input_ids[0][-len(stop_ids):], stop_ids).all():
                return True
        return False

stopping_criteria = StoppingCriteriaList([StopOnTokens()])

generate_text = transformers.pipeline(
    model=model, 
    tokenizer=tokenizer,
    return_full_text=True,  # langchain expects the full text
    task='text-generation',
    # we pass model parameters here too
    stopping_criteria=stopping_criteria,  # without this model rambles during chat
    temperature=0.1,  # 'randomness' of outputs, 0.0 is the min and 1.0 the max
    max_new_tokens=512,  # max number of tokens to generate in the output
    repetition_penalty=1.1  # without this output begins repeating
)

# res = generate_text("Explain me the difference between Data Lakehouse and Data Warehouse.")
# print(res[0]["generated_text"])

while True:
    user_input = input("请输入您的问题（输入 'exit' 退出）: ")

    if user_input.lower() == 'exit':
        print("退出程序。")
        break

    print("Answer:\n")
    print(generate_text(user_input)[0]["generated_text"])