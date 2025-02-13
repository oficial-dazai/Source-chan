import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import pickle
import os

FILE_PATH = os.path.join("data", "estado_tarefas.pkl")

# Funções para salvar e carregar o estado das mensagens
def salvar_estado(mensagens):
    # Garante que a pasta "data" exista
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
    with open(FILE_PATH, "wb") as f:
        pickle.dump(mensagens, f)

def carregar_estado():
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "rb") as f:
            return pickle.load(f)
    return {}

# Carrega o estado salvo
# O estado agora armazenará: título, tarefas, índice, marcações, channel_id
mensagens = carregar_estado()

class TaskManager:
    def __init__(self, titulo, tarefas, index_selecionado=0, concluidas=None):
        self.titulo = titulo.strip()
        self.tarefas = [t.strip() for t in tarefas]
        self.index_selecionado = index_selecionado
        self.concluidas = concluidas if concluidas else [False] * len(self.tarefas)

    def calcular_porcentagem(self):
        if not self.tarefas:
            return 0
        total_concluidas = sum(self.concluidas)
        return round((total_concluidas / len(self.tarefas)) * 100)

    def formatar_lista(self):
        porcentagem = self.calcular_porcentagem()
        lista_formatada = [f"# {self.titulo} `({porcentagem}%)`"]
        for i, tarefa in enumerate(self.tarefas):
            prefixo = "<a:setawhite:1339687866451759236> " if i == self.index_selecionado else "   "
            status = "<:check:1339687857010249894>" if self.concluidas[i] else "<:nocheck:1339687841936183387>"
            lista_formatada.append(f"{prefixo}{status} {tarefa}")
        return "\n".join(lista_formatada)

    def mover_cima(self):
        if self.index_selecionado > 0:
            self.index_selecionado -= 1

    def mover_baixo(self):
        if self.index_selecionado < len(self.tarefas) - 1:
            self.index_selecionado += 1

    def marcar_concluida(self):
        self.concluidas[self.index_selecionado] = not self.concluidas[self.index_selecionado]

# Modal para editar a lista de tarefas
class EditTaskModal(Modal, title="Editar Lista de Tarefas"):
    novo_titulo = TextInput(label="Novo Título", placeholder="Digite o novo título (opcional)", required=False)
    nova_entrada = TextInput(
        label="Novas Tarefas", 
        style=discord.TextStyle.long,
        placeholder="Digite as novas tarefas separadas por ';' (opcional)", 
        required=False
    )

    def __init__(self, view: "TaskView"):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        # Atualiza o título se fornecido
        if self.novo_titulo.value:
            self.view.manager.titulo = self.novo_titulo.value.strip()
        # Atualiza a lista de tarefas se fornecido
        if self.nova_entrada.value:
            novas_tarefas = [t.strip() for t in self.nova_entrada.value.split(';')]
            self.view.manager.tarefas = novas_tarefas
            # Reseta as marcações e o índice
            self.view.manager.concluidas = [False] * len(novas_tarefas)
            self.view.manager.index_selecionado = 0
        await self.view.atualizar_mensagem()
        await interaction.response.send_message("Lista editada com sucesso!", ephemeral=True)

class TaskView(View):
    def __init__(self, manager, interaction, mensagem_id, channel_id=None):
        super().__init__(timeout=None)
        self.manager = manager
        self.interaction = interaction  # A interação original (pode ser None se restaurado)
        self.mensagem_id = mensagem_id
        self.channel_id = channel_id  # Armazena o canal onde a mensagem foi enviada
        self.message = None  # Aqui será armazenada a mensagem real após restaurá-la

    async def atualizar_mensagem(self):
        lista_formatada = self.manager.formatar_lista()
        if self.interaction:
            # Se a interação estiver disponível, use-a para editar a mensagem
            await self.interaction.edit_original_response(content=lista_formatada, view=self)
        elif self.message:
            # Se não há interação, mas temos a mensagem (restaurada), edite-a diretamente
            try:
                await self.message.edit(content=lista_formatada, view=self)
            except Exception as e:
                print("Erro ao editar a mensagem restaurada:", e)
        # Atualiza o estado persistente, incluindo channel_id
        mensagens[self.mensagem_id] = {
            "titulo": self.manager.titulo,
            "tarefas": self.manager.tarefas,
            "index_selecionado": self.manager.index_selecionado,
            "concluidas": self.manager.concluidas,
            "channel_id": self.channel_id,
        }
        salvar_estado(mensagens)

    @discord.ui.button(label="Subir", style=discord.ButtonStyle.primary, custom_id="botao_subir")
    async def subir(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.manager.mover_cima()
        self.interaction = interaction
        await self.atualizar_mensagem()

    @discord.ui.button(label="Descer", style=discord.ButtonStyle.primary, custom_id="botao_descer")
    async def descer(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.manager.mover_baixo()
        self.interaction = interaction
        await self.atualizar_mensagem()

    @discord.ui.button(label="Concluir", style=discord.ButtonStyle.success, custom_id="botao_concluir")
    async def concluir(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.manager.marcar_concluida()
        self.interaction = interaction
        await self.atualizar_mensagem()

    @discord.ui.button(label="Editar", style=discord.ButtonStyle.secondary, custom_id="botao_editar")
    async def editar(self, interaction: discord.Interaction, button: Button):
        modal = EditTaskModal(self)
        await interaction.response.send_modal(modal)

# Define o comando slash "tarefas" fora de qualquer cog
@app_commands.command(name="tarefas", description="Cria uma lista de tarefas com título.")
@app_commands.describe(titulo="Título da lista", entrada="Tarefas separadas por ';'")
async def tarefas(interaction: discord.Interaction, titulo: str, entrada: str):
    await interaction.response.defer()
    tarefas_list = [t.strip() for t in entrada.split(';')]
    manager = TaskManager(titulo, tarefas_list)
    # Envia a mensagem e obtém o objeto mensagem para capturar o canal
    mensagem = await interaction.followup.send(manager.formatar_lista())
    # Cria a view e registra o ID da mensagem e canal
    view = TaskView(manager, interaction, mensagem.id, mensagem.channel.id)
    await mensagem.edit(view=view)
    # Salva o estado da mensagem (incluindo o canal)
    mensagens[mensagem.id] = {
        "titulo": titulo,
        "tarefas": tarefas_list,
        "index_selecionado": manager.index_selecionado,
        "concluidas": manager.concluidas,
        "channel_id": mensagem.channel.id,
    }
    salvar_estado(mensagens)

# Função para registrar o comando e restaurar as views persistentes
def register_task_list(bot: commands.Bot):
    # Tenta ler o GUILD_ID do ambiente para registrar o comando como guild específico
    guild_id = os.getenv("GUILD_ID")
    if guild_id:
        guild_obj = discord.Object(id=int(guild_id))
        bot.tree.add_command(tarefas, guild=guild_obj)
        print(f"Comando /tarefas adicionado para a guild {guild_id}.")
    else:
        bot.tree.add_command(tarefas)
        print("Comando /tarefas adicionado globalmente.")

    # Função interna para restaurar as views persistentes quando o bot estiver pronto
    async def restore_views():
        await bot.wait_until_ready()
        for mensagem_id, dados in mensagens.copy().items():
            manager = TaskManager(
                dados["titulo"],
                dados["tarefas"],
                dados.get("index_selecionado", 0),
                dados.get("concluidas", [False] * len(dados["tarefas"]))
            )
            channel_id = dados.get("channel_id")
            view = TaskView(manager, None, mensagem_id, channel_id)
            # Tenta buscar a mensagem para reatribuir à view
            if channel_id:
                try:
                    channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
                    msg = await channel.fetch_message(mensagem_id)
                    view.message = msg  # Armazena a mensagem na view
                    await msg.edit(content=manager.formatar_lista(), view=view)
                except Exception as e:
                    print(f"Erro ao restaurar a mensagem {mensagem_id} no canal {channel_id}: {e}")
            bot.add_view(view, message_id=mensagem_id)
        print("Views persistentes restauradas!")
    bot.add_listener(restore_views, "on_ready")
