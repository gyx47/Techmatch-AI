# fix_tokenizer.py
import os
import json

def fix_tokenizer_files():
    model_dir = "./models/paraphrase-multilingual-MiniLM-L12-v2"
    
    print("修复 tokenizer 文件...")
    
    # 1. 创建必要的文件
    vocab_path = os.path.join(model_dir, "vocab.txt")
    
    # 如果 vocab.txt 不存在或很小，重建
    if not os.path.exists(vocab_path) or os.path.getsize(vocab_path) < 100:
        print("创建 vocab.txt...")
        with open(vocab_path, 'w', encoding='utf-8') as f:
            # 必需的特殊标记
            f.write("[PAD]\n")
            f.write("[UNK]\n")
            f.write("[CLS]\n")
            f.write("[SEP]\n")
            f.write("[MASK]\n")
            f.write("<|endoftext|>\n")
            
            # 添加基本字符
            for i in range(10):
                f.write(f"{i}\n")
            
            for i in range(ord('A'), ord('Z')+1):
                f.write(f"{chr(i)}\n")
            
            for i in range(ord('a'), ord('z')+1):
                f.write(f"{chr(i)}\n")
            
            # 添加一些中文常用字
            common_chinese = "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头条基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海"
            for char in common_chinese:
                f.write(f"{char}\n")
        
        print(f"✅ 创建了 vocab.txt，包含 {len(common_chinese)+100} 个标记")
    
    # 2. 更新 tokenizer_config.json
    tokenizer_config_path = os.path.join(model_dir, "tokenizer_config.json")
    if os.path.exists(tokenizer_config_path):
        try:
            with open(tokenizer_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            config = {}
    else:
        config = {}
    
    # 确保有必要的配置
    config.update({
        "unk_token": "[UNK]",
        "pad_token": "[PAD]",
        "cls_token": "[CLS]",
        "sep_token": "[SEP]",
        "mask_token": "[MASK]",
        "model_max_length": 512,
        "do_lower_case": False,
        "do_basic_tokenize": True,
        "never_split": ["[UNK]", "[PAD]", "[CLS]", "[SEP]", "[MASK]"],
        "tokenize_chinese_chars": True
    })
    
    with open(tokenizer_config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("✅ 更新了 tokenizer_config.json")
    
    # 3. 测试
    print("\n测试模型加载...")
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_dir)
        print("✅ 模型加载成功！")
        
        # 简单测试
        texts = ["hello", "world", "测试"]
        embeddings = model.encode(texts)
        print(f"✅ 编码成功！形状: {embeddings.shape}")
        
    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}")
        print(f"   信息: {str(e)[:200]}")

if __name__ == "__main__":
    fix_tokenizer_files()