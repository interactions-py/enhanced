from random import randint

from typing_extensions import Annotated

from interactions import ActionRow, Button, ButtonStyle, Client, CommandContext, ComponentContext
from interactions.ext.enhanced import EnhancedOption, SubcommandSetup

client = Client("...")
client.load("interactions.ext.enhanced", debug_scope=123456789)


@client.event
async def on_ready():
    print("Ready!")


@client.command(debug_scope=False)
async def send_buttons(ctx: CommandContext):
    """Sends buttons!"""
    example_id: int = randint(0, 999_999_999)
    await ctx.send(
        "Pong!",
        components=ActionRow(
            components=[
                Button(
                    style=ButtonStyle.PRIMARY,
                    custom_id=f"primary{example_id}",
                    label="Primary",
                ),
                Button(
                    style=ButtonStyle.SECONDARY,
                    custom_id=f"secondary{example_id}",
                    label="Secondary",
                ),
            ]
        ),
    )


@client.component("primary", startswith=True)
async def primary_callback(ctx: ComponentContext):
    custom_id: str = ctx.data.custom_id
    await ctx.send(f"You clicked on a primary button! ID is {custom_id.replace('primary', '')}")


@client.component("secondary", startswith=True)
async def secondary_callback(ctx: ComponentContext):
    custom_id: str = ctx.data.custom_id
    await ctx.send(f"You clicked on a secondary button! ID is {custom_id.replace('secondary', '')}")


@client.command()
async def command_with_options(
    ctx: CommandContext,
    string: Annotated[str, EnhancedOption(description="String")],
    integer: Annotated[int, EnhancedOption(description="Integer")] = 5,
):
    """Command with options!"""
    await ctx.send(f"String: {string}, Integer: {integer}")


base: SubcommandSetup = client.subcommand_base("base", description="Base")


@base.subcommand(group="subcommand_group")
async def subcommand(ctx: CommandContext):
    """Subcommand"""
    await ctx.send("Subcommand")


@base.subcommand(group="subcommand_group")
async def subcommand_options(
    ctx: CommandContext,
    string: Annotated[str, EnhancedOption(description="String")],
    integer: Annotated[int, EnhancedOption(description="Integer")] = 5,
):
    """Subcommand with options"""
    await ctx.send(f"Subcommand with options: {string=}, {integer=}.")


@base.subcommand()
async def subcommand_no_group(ctx: CommandContext):
    """Subcommand without group"""
    await ctx.send("Subcommand without group")


base.finish()


client.load("enhanced_extension")
client.start()
