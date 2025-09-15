def load_config(broker_name):
    from config import BROKER_CONFIG
    return BROKER_CONFIG.get(broker_name, {})
