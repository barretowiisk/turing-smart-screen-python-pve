# Instalar o Turing Smart Screen com o tema ProxmoxPVE

Este guia instala o aplicativo original no host Proxmox VE, aplica **manualmente** os arquivos deste repositório e configura o LCD para iniciar automaticamente em segundo plano.

**Resultado:** LCD USB 3.5″, revisão A / USBMONITOR_3_5, landscape 480×320, com CPU, RAM, root STORAGE, VM, LXC, uptime, load, servidor, data e hora.

Todos os comandos abaixo são para o **Shell do host PVE, como root**. Não os execute no Windows nem dentro de uma VM/LXC.

## 1. Preparar o host e conectar o LCD

Conecte o LCD diretamente ao USB do host usando um cabo de dados.

```bash
apt update
apt install -y git python3 python3-venv python3-pip python3-dev python3-tk \
  build-essential libjpeg-dev zlib1g-dev libusb-1.0-0 lm-sensors usbutils

pveversion
python3 --version
lsusb
ls -l /dev/ttyACM* /dev/serial/by-id/ 2>/dev/null
```

Use os repositórios Debian/PVE já configurados. Resolva eventuais erros do `apt update` antes de continuar. Não é necessário atualizar todo o PVE ou reiniciá-lo para instalar o tema.

É comum que a porta apareça como `/dev/ttyACM0`. O padrão `AUTO` tenta descobri-la. Como usamos root, normalmente não é necessário alterar permissões. Para um usuário diferente, o grupo `dialout` pode resolver o acesso serial (`usermod -aG dialout NOME_DO_USUARIO`, seguido de nova sessão), mas isso **não concede permissões para consultar o Proxmox**. O serviço deste guia executa como root. Não use `chmod 777` na porta.

## 2. Clonar o aplicativo original atualizado

Em uma instalação nova:

```bash
git clone https://github.com/mathoudebine/turing-smart-screen-python.git /opt/turing-smart-screen-python
cd /opt/turing-smart-screen-python
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m pip check
git rev-parse HEAD
```

O clone obtém a revisão atual da branch padrão do upstream naquele momento. As bibliotecas são instaladas a partir do `requirements.txt` dessa revisão. Não use o Python global nem `--break-system-packages`.

Se `/opt/turing-smart-screen-python` já existe, não clone por cima. Para atualizar uma instalação existente com segurança, use a seção 10.

Registre o SHA retornado pelo último comando após validar o funcionamento. Para reproduzir exatamente essa revisão em outro host, use `git checkout --detach SHA_VALIDADO` depois do clone e antes da instalação das dependências. Usar sempre a revisão mais recente exige nova validação: não garante a mesma API em versões futuras.

## 3. Clonar o tema separadamente

```bash
git clone https://github.com/barretowiisk/turing-smart-screen-python-pve.git /opt/turing-smart-screen-python-pve
```

As pastas têm funções diferentes:

| Pasta | Conteúdo |
| --- | --- |
| `/opt/turing-smart-screen-python` | Aplicativo upstream, venv e instalação ativa |
| `/opt/turing-smart-screen-python-pve` | Arquivos deste tema, usados como origem da cópia |

Não execute `main.py` na pasta do tema: ela não contém o aplicativo completo.

## 4. Fazer backup e sobrepor manualmente

Se `main.py` estiver rodando manualmente, encerre com **Ctrl+C**. Se já houver serviço ativo, pare-o:

```bash
systemctl stop turing-smart-screen.service
```

Na primeira instalação o serviço ainda não existe; nesse caso, pule esse comando.

Faça um backup dos arquivos que serão substituídos:

```bash
BACKUP="/opt/turing-pve-backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP/library/sensors" "$BACKUP/res/themes"
cp -a /opt/turing-smart-screen-python/config.yaml "$BACKUP/config.yaml"
cp -a /opt/turing-smart-screen-python/library/sensors/sensors_custom.py "$BACKUP/library/sensors/"
if [ -d /opt/turing-smart-screen-python/res/themes/ProxmoxPVE ]; then
  cp -a /opt/turing-smart-screen-python/res/themes/ProxmoxPVE "$BACKUP/res/themes/"
fi
printf 'Backup: %s\n' "$BACKUP"
```

Copie as customizações:

```bash
mkdir -p /opt/turing-smart-screen-python/res/themes/ProxmoxPVE
cp /opt/turing-smart-screen-python-pve/res/themes/ProxmoxPVE/theme.yaml \
   /opt/turing-smart-screen-python/res/themes/ProxmoxPVE/theme.yaml
cp /opt/turing-smart-screen-python-pve/res/themes/ProxmoxPVE/background.png \
   /opt/turing-smart-screen-python/res/themes/ProxmoxPVE/background.png
cp /opt/turing-smart-screen-python-pve/library/sensors/sensors_custom.py \
   /opt/turing-smart-screen-python/library/sensors/sensors_custom.py
cp /opt/turing-smart-screen-python-pve/config.yaml \
   /opt/turing-smart-screen-python/config.yaml
```

**Essa sobreposição substitui o config e o arquivo completo de sensores customizados.** É o caminho simples para uma instalação nova. Se você já possui outros sensores, ou se a interface `CustomDataSource` mudou no upstream, faça a integração manual: mantenha a base upstream e transfira apenas o bloco iniciado por `# Proxmox VE - lightweight custom sensors`, incluindo imports, cache e classes até `ProxmoxTime`. Remova a versão Proxmox anterior antes de colar para não duplicar classes.

Ao atualizar um config existente, você também pode editar somente as opções da próxima seção, preservando as demais opções da nova revisão upstream.

## 5. Conferir a configuração

```bash
nano /opt/turing-smart-screen-python/config.yaml
```

Confira estas opções dentro das respectivas seções existentes; não crie seções duplicadas:

```yaml
config:
  COM_PORT: AUTO
  THEME: ProxmoxPVE
  HW_SENSORS: PYTHON

display:
  REVISION: A
  BRIGHTNESS: 80
  DISPLAY_REVERSE: false
  RESET_ON_STARTUP: true
```

O arquivo do repositório contém outras opções do aplicativo. A interface de rede pode ficar vazia se não for utilizada pelo tema. `USBMONITOR_3_5` é a identificação da sub-revisão pelo driver, não uma chave adicional no config.

- **Brilho:** escolha entre 0 e 100; 80 é o valor do arquivo fornecido. A revisão A pode aquecer com brilho elevado.
- **Porta:** se AUTO não funcionar, use a porta observada, por exemplo `COM_PORT: /dev/ttyACM0`.
- **Orientação:** está no `theme.yaml`, com `DISPLAY_ORIENTATION: landscape` e `DISPLAY_SIZE: 3.5"`.
- **Reset:** mantenha `true` no estado padrão. Ele pode causar reconexão e mudança de porta; AUTO ajuda na descoberta.

## 6. Validar sensores, YAML e imagem

```bash
cd /opt/turing-smart-screen-python
./venv/bin/python -m py_compile library/sensors/sensors_custom.py
./venv/bin/python -m pip check
./venv/bin/python -m serial.tools.list_ports -v
pvesh get /cluster/resources --type vm --output-format json

./venv/bin/python - <<'PY'
import yaml
import psutil
from PIL import Image
from library.sensors import sensors_custom as s

with open('config.yaml', encoding='utf-8') as f:
    config = yaml.safe_load(f)
with open('res/themes/ProxmoxPVE/theme.yaml', encoding='utf-8') as f:
    theme = yaml.safe_load(f)
assert config['config']['THEME'] == 'ProxmoxPVE'
assert config['config']['HW_SENSORS'] == 'PYTHON'
assert config['display']['REVISION'] == 'A'
assert theme['display']['DISPLAY_SIZE'] == '3.5"'
assert theme['display']['DISPLAY_ORIENTATION'] == 'landscape'
with Image.open('res/themes/ProxmoxPVE/background.png') as image:
    assert image.format == 'PNG' and image.size == (480, 320)
    image.load()
print('Config, tema e PNG 480x320: OK')
print('Root:', psutil.disk_usage('/').percent, '%')
print('Temperaturas:', psutil.sensors_temperatures())
for name in ('ProxmoxVMs', 'ProxmoxCTs', 'ProxmoxUptime', 'ProxmoxLoad',
             'ProxmoxServer', 'ProxmoxDate', 'ProxmoxTime'):
    print(name, getattr(s, name)().as_string())
PY
```

VM/LXC mostram `running/total` do nó local. O código atual filtra pelo hostname; compare `hostname` com o campo `node` retornado pelo pvesh se aparecer `0/0` inesperadamente. Templates também podem entrar no total quando retornados pelo endpoint.

As duas classes compartilham um cache de cerca de 20 segundos **após sucesso**. Em falhas, a versão atual pode repetir a tentativa nas leituras seguintes e reutilizar dados antigos; sem dados anteriores, retorna uma lista vazia, que pode aparecer como `0/0`. Por isso, valide o comando pvesh diretamente em caso de dúvida.

Uptime usa `/proc/uptime`, load usa `os.getloadavg()[0]`, SERVER cacheia hostname/versão durante o processo e data/hora usam `%d/%m/%Y` e `%H:%M`. O fuso vem do host. O tema atual usa `CUSTOM.INTERVAL: 20`; a virada do minuto pode atrasar aproximadamente 20 segundos. Você pode reduzir esse intervalo para 10, mantendo o cache dos guests em 20.

## 7. Testar o LCD manualmente

Com o serviço parado:

```bash
cd /opt/turing-smart-screen-python
./venv/bin/python main.py
```

Confira o carregamento do tema, comunicação com revisão A, background, orientação, valores e atualizações. Observe uma mudança de números para conferir se o fundo está sendo restaurado corretamente.

Encerre com **Ctrl+C** antes da próxima etapa. Nunca execute o serviço e uma instância manual ao mesmo tempo na mesma porta USB.

## 8. Habilitar segundo plano e início automático

Crie o serviço:

```bash
cat > /etc/systemd/system/turing-smart-screen.service <<'EOF'
[Unit]
Description=Turing Smart Screen - Painel Proxmox VE
Wants=network-online.target
After=network-online.target pve-cluster.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=root
WorkingDirectory=/opt/turing-smart-screen-python
ExecStart=/opt/turing-smart-screen-python/venv/bin/python /opt/turing-smart-screen-python/main.py
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=10
KillSignal=SIGINT
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now turing-smart-screen.service
systemctl status turing-smart-screen.service --no-pager
systemctl is-enabled turing-smart-screen.service
```

Espere **active (running)** e **enabled**. Agora pode fechar o SSH. O serviço tenta reiniciar o processo após 10 segundos caso ele encerre, inclusive se sair com código zero. A ordenação após `pve-cluster` não garante disponibilidade imediata da API; os sensores tentarão consultá-la nas próximas leituras.

Comandos do dia a dia:

```bash
# Ver logs em tempo real; Ctrl+C encerra apenas esta visualização
journalctl -u turing-smart-screen.service -f

# Aplicar mudanças de tema, sensores ou brilho
systemctl restart turing-smart-screen.service

# Parar e voltar a iniciar
systemctl stop turing-smart-screen.service
systemctl start turing-smart-screen.service
```

No próximo reboot planejado, confira o LCD e `journalctl -b -u turing-smart-screen.service --no-pager`. Não é preciso reiniciar o host agora apenas para instalar o painel.

## 9. Ajustes e solução de problemas

| Situação | Como resolver |
| --- | --- |
| `No supported GPU found` com Intel integrado | Esperado neste cenário; o tema não mostra GPU. CPU/RAM/PVE continuam independentes. |
| Aviso de tray icon no SSH | Normal em ambiente sem desktop; confira se o painel continua executando. |
| LCD não encontrado | Confira cabo USB de dados, `lsusb`, portas e `dmesg -T`. Teste porta explícita no config. |
| Porta ocupada | Pare a outra instância de main.py ou o serviço antes do teste manual. |
| Reset faz o LCD perder comunicação | Confira se a porta mudou. Prefira AUTO; se esse hardware não tolerar reset, teste `RESET_ON_STARTUP: false` como exceção. |
| Temperatura ausente | Rode `sensors` e confira os sensores Python. Em Intel compatível, teste `modprobe coretemp`; só persista o módulo depois de confirmar funcionamento. |
| Hora errada | Confira `timedatectl`: formato e fuso são coisas distintas. O formato já é 24h. |
| SERVER mostra versão antiga | Reinicie após atualizar o PVE, pois a versão é cacheada durante a execução. |
| Alterar X/Y não move o texto | Edite o tema ativo em `/opt/turing-smart-screen-python/res/themes/ProxmoxPVE/theme.yaml` e reinicie o serviço. |
| Imagem distorcida ou ghosting | Confirme PNG físico 480×320, landscape, instância única e áreas de restauração adequadas. |
| Falha só no systemd | Confira caminho do venv, WorkingDirectory e `journalctl -u turing-smart-screen.service -n 100 --no-pager`. |

### Background e áreas de texto

O PNG distribuído já tem 480×320. Definir esse tamanho apenas no YAML **não altera o tamanho físico de uma imagem substituta**. Como `BACKGROUND_IMAGE` é usado para restaurar regiões, uma imagem maior pode causar recortes incompatíveis.

Se precisar converter outra imagem, faça backup primeiro e use:

```bash
cd /opt/turing-smart-screen-python
cp res/themes/ProxmoxPVE/background.png /opt/background-turing-original.png
./venv/bin/python - <<'PY'
from PIL import Image
path = 'res/themes/ProxmoxPVE/background.png'
with Image.open(path) as image:
    image.convert('RGB').resize((480, 320), Image.Resampling.LANCZOS).save(path)
PY
systemctl restart turing-smart-screen.service
```

Uma imagem de proporção diferente será deformada; prefira exportar o desenho diretamente em 480×320. Mantenha `BACKGROUND_IMAGE: background.png` nos campos dinâmicos, com `WIDTH/HEIGHT` suficientes para os valores e sem invadir outros campos. Hostnames longos ou contagens grandes podem exigir fonte menor. Reinicie depois de qualquer ajuste em coordenadas, fonte ou tamanho.

## 10. Atualizar o upstream e reaplicar o tema

As atualizações são manuais. Não configure atualização automática no boot: uma mudança de dependências ou API deve ser testada antes de substituir a instalação funcional.

Para atualizar apenas a origem do tema:

```bash
cd /opt/turing-smart-screen-python-pve
git status --short
git pull --ff-only
```

Se houver alterações locais, salve-as ou resolva o conflito antes de prosseguir. O pull não altera a instalação ativa; repita o backup e a sobreposição da seção 4 quando quiser aplicar as mudanças.

Para obter o upstream mais recente, preserve a instalação atual inteira e crie uma nova:

```bash
systemctl stop turing-smart-screen.service
STAMP=$(date +%Y%m%d-%H%M%S)
OLD="/opt/turing-smart-screen-python.backup-$STAMP"
cd /opt/turing-smart-screen-python
git rev-parse HEAD > "/opt/turing-upstream-$STAMP.txt"
./venv/bin/python -m pip freeze > "/opt/turing-dependencias-$STAMP.txt"
cd /opt
mv /opt/turing-smart-screen-python "$OLD"
printf 'Backup completo: %s\n' "$OLD"

git clone https://github.com/mathoudebine/turing-smart-screen-python.git /opt/turing-smart-screen-python
cd /opt/turing-smart-screen-python
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
```

Depois:

1. Reaplique os arquivos manualmente conforme a seção 4. Se ajustou o tema localmente, use a versão salva em `$OLD` ou incorpore suas alterações na origem antes da cópia.
2. Confira diferenças da interface `CustomDataSource` e preserve novas opções necessárias do config upstream.
3. Ajuste brilho e porta novamente conforme a seção 5.
4. Repita os testes Python/YAML e LCD das seções 6 e 7.
5. Inicie com `systemctl start turing-smart-screen.service` e registre o novo SHA validado.

Não copie o venv para outros hosts. No backup, ele deve ser reutilizado somente depois de restaurar a pasta ao caminho original, pois seus scripts podem conter caminhos absolutos.

### Rollback da atualização

Use o caminho de backup exibido acima, substituindo `DATA-HORA` pelo valor real:

```bash
systemctl stop turing-smart-screen.service
cd /opt
mv /opt/turing-smart-screen-python "/opt/turing-smart-screen-python.failed-$(date +%Y%m%d-%H%M%S)"
mv /opt/turing-smart-screen-python.backup-DATA-HORA /opt/turing-smart-screen-python
systemctl start turing-smart-screen.service
```

Se o novo clone nem chegou a criar a pasta, pule o primeiro `mv`. Mantenha os backups até confirmar estabilidade. Para reverter só a sobreposição do tema, restaure os arquivos correspondentes de `/opt/turing-pve-backups/DATA-HORA/`, com o serviço parado.

## Referências e escopo

- [Aplicativo original](https://github.com/mathoudebine/turing-smart-screen-python)
- [Instalação upstream](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start)
- [Configuração de comunicação e display](https://github.com/mathoudebine/turing-smart-screen-python/blob/main/config.yaml)
- [Interface dos sensores customizados](https://github.com/mathoudebine/turing-smart-screen-python/blob/main/library/sensors/sensors_custom.py)

O guia descreve os arquivos deste repositório e a instalação discutida pelo autor. O teste local da documentação não substitui a validação no LCD físico, no boot do PVE ou em uma revisão futura do upstream.
