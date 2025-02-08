import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import pickle
import os

# Funções para salvar e carregar o estado das mensagens
def salvar_estado(mensagens):
    with open("estado_tarefas.pkl", "wb") as f:
        pickle.dump(mensagens, f)

def carregar_estado():
    if os.path.exists("estado_tarefas.pkl"):
        with open("estado_tarefas.pkl", "rb") as f:
            return pickle.load(f)
    return {}

# Carrega o estado salvo
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
        lista_formatada = [f"# {self.titulo} ({porcentagem}%)"]
        for i, tarefa in enumerate(self.tarefas):
            prefixo = "→ " if i == self.index_selecionado else "   "
            status = "✓" if self.concluidas[i] else "✕"
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

class TaskView(View):
    def __init__(self, manager, interaction, mensagem_id):
        super().__init__(timeout=None)
        self.manager = manager
        self.interaction = interaction
        self.mensagem_id = mensagem_id

    async def atualizar_mensagem(self):
        if self.interaction:
            lista_formatada = self.manager.formatar_lista()
            await self.interaction.edit_original_response(content=lista_formatada, view=self)
        # Atualiza o estado persistente
        mensagens[self.mensagem_id] = {
            "titulo": self.manager.titulo,
            "tarefas": self.manager.tarefas,
            "index_selecionado": self.manager.index_selecionado,
            "concluidas": self.manager.concluidas
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

# Define o comando slash "tarefas" fora de qualquer cog
@app_commands.command(name="tarefas", description="Cria uma lista de tarefas com título.")
@app_commands.describe(titulo="Título da lista", entrada="Tarefas separadas por ';'")
async def tarefas(interaction: discord.Interaction, titulo: str, entrada: str):
    await interaction.response.defer()

    tarefas_list = [t.strip() for t in entrada.split(';')]
    manager = TaskManager(titulo, tarefas_list)
    view = TaskView(manager, interaction, None)
    lista_formatada = manager.formatar_lista()

    mensagem = await interaction.followup.send(lista_formatada, view=view)

    # Salva o estado da mensagem
    mensagens[mensagem.id] = {
        "titulo": titulo,
        "tarefas": tarefas_list,
        "index_selecionado": manager.index_selecionado,
        "concluidas": manager.concluidas,
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

    # Define uma função interna para restaurar as views persistentes quando o bot estiver pronto
    async def restore_views():
        await bot.wait_until_ready()
        for mensagem_id, dados in mensagens.items():
            manager = TaskManager(
                dados["titulo"],
                dados["tarefas"],
                dados.get("index_selecionado", 0),
                dados.get("concluidas", [False] * len(dados["tarefas"]))
            )
            view = TaskView(manager, None, mensagem_id)
            bot.add_view(view, message_id=mensagem_id)
        print("Views persistentes restauradas!")

    # Adiciona o listener para o evento on_ready
    bot.add_listener(restore_views, "on_ready")
