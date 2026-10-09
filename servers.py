# servers.py

PLANS = [
    {"id": "1m",  "name": "1 месяц",  "days": 30,    "price": 75},
    {"id": "2m",  "name": "2 месяца", "days": 60,    "price": 150},
    {"id": "1y",  "name": "1 год",    "days": 365,   "price": 900},
    {"id": "inf", "name": "Навсегда", "days": 36500, "price": 1590},
]

SERVERS = [
    {"id": "de-1", "name": "🇩🇪 Германия — Frankfurt",
     "link": "vless://YOUR_UUID@de1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#DE-Frankfurt"},
    {"id": "de-2", "name": "🇩🇪 Германия — Berlin",
     "link": "vless://YOUR_UUID@de2.example.com:443?type=tcp&security=reality&sni=www.microsoft.com&fp=chrome#DE-Berlin"},
    {"id": "nl-1", "name": "🇳🇱 Нидерланды — Amsterdam",
     "link": "vless://YOUR_UUID@nl1.example.com:443?type=tcp&security=reality&sni=www.microsoft.com&fp=chrome#NL-Amsterdam"},
    {"id": "fr-1", "name": "🇫🇷 Франция — Paris",
     "link": "vless://YOUR_UUID@fr1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#FR-Paris"},
    {"id": "gb-1", "name": "🇬🇧 Великобритания — London",
     "link": "vless://YOUR_UUID@gb1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#GB-London"},
    {"id": "fi-1", "name": "🇫🇮 Финляндия — Helsinki",
     "link": "vless://YOUR_UUID@fi1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#FI-Helsinki"},
    {"id": "se-1", "name": "🇸🇪 Швеция — Stockholm",
     "link": "vless://YOUR_UUID@se1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#SE-Stockholm"},
    {"id": "pl-1", "name": "🇵🇱 Польша — Warsaw",
     "link": "vless://YOUR_UUID@pl1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#PL-Warsaw"},
    {"id": "ch-1", "name": "🇨🇭 Швейцария — Zurich",
     "link": "vless://YOUR_UUID@ch1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#CH-Zurich"},
    {"id": "at-1", "name": "🇦🇹 Австрия — Vienna",
     "link": "vless://YOUR_UUID@at1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#AT-Vienna"},
    {"id": "es-1", "name": "🇪🇸 Испания — Madrid",
     "link": "vless://YOUR_UUID@es1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#ES-Madrid"},
    {"id": "it-1", "name": "🇮🇹 Италия — Milan",
     "link": "vless://YOUR_UUID@it1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#IT-Milan"},
    {"id": "cz-1", "name": "🇨🇿 Чехия — Prague",
     "link": "vless://YOUR_UUID@cz1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#CZ-Prague"},
    {"id": "ro-1", "name": "🇷🇴 Румыния — Bucharest",
     "link": "vless://YOUR_UUID@ro1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#RO-Bucharest"},
    {"id": "us-1", "name": "🇺🇸 США — New York",
     "link": "trojan://YOUR_PASSWORD@us1.example.com:443?security=tls&sni=us1.example.com#US-NewYork"},
    {"id": "us-2", "name": "🇺🇸 США — Los Angeles",
     "link": "trojan://YOUR_PASSWORD@us2.example.com:443?security=tls&sni=us2.example.com#US-LosAngeles"},
    {"id": "ca-1", "name": "🇨🇦 Канада — Toronto",
     "link": "trojan://YOUR_PASSWORD@ca1.example.com:443?security=tls&sni=ca1.example.com#CA-Toronto"},
    {"id": "br-1", "name": "🇧🇷 Бразилия — São Paulo",
     "link": "trojan://YOUR_PASSWORD@br1.example.com:443?security=tls&sni=br1.example.com#BR-SaoPaulo"},
    {"id": "tr-1", "name": "🇹🇷 Турция — Istanbul",
     "link": "vless://YOUR_UUID@tr1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#TR-Istanbul"},
    {"id": "jp-1", "name": "🇯🇵 Япония — Tokyo",
     "link": "vless://YOUR_UUID@jp1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#JP-Tokyo"},
    {"id": "sg-1", "name": "🇸🇬 Сингапур",
     "link": "vless://YOUR_UUID@sg1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#SG-Singapore"},
    {"id": "kr-1", "name": "🇰🇷 Южная Корея — Seoul",
     "link": "vless://YOUR_UUID@kr1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#KR-Seoul"},
    {"id": "in-1", "name": "🇮🇳 Индия — Mumbai",
     "link": "vless://YOUR_UUID@in1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#IN-Mumbai"},
    {"id": "ae-1", "name": "🇦🇪 ОАЭ — Dubai",
     "link": "vless://YOUR_UUID@ae1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#AE-Dubai"},
    {"id": "kz-1", "name": "🇰🇿 Казахстан — Almaty",
     "link": "vless://YOUR_UUID@kz1.example.com:443?type=tcp&security=reality&sni=www.google.com&fp=chrome#KZ-Almaty"},
]

REGIONS = {
    "eu": {
        "name": "🇪🇺 Европа",
        "server_ids": ["de-1", "de-2", "nl-1", "fr-1", "gb-1", "fi-1",
                       "se-1", "pl-1", "ch-1", "at-1", "es-1", "it-1",
                       "cz-1", "ro-1"],
    },
    "am": {
        "name": "🌎 Америка",
        "server_ids": ["us-1", "us-2", "ca-1", "br-1"],
    },
    "as": {
        "name": "🌏 Азия и Ближний Восток",
        "server_ids": ["tr-1", "jp-1", "sg-1", "kr-1", "in-1", "ae-1", "kz-1"],
    },
}


def find_plan(plan_id: str):
    for p in PLANS:
        if p["id"] == plan_id:
            return p
    return None


def find_server(server_id: str):
    for s in SERVERS:
        if s["id"] == server_id:
            return s
    return None