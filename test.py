import yaml
with open('info.yml', "r", encoding="utf-8",errors='ignore') as f:
    config = yaml.safe_load(f)['prior']
print(config)