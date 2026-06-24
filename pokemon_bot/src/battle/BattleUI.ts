import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder } from 'discord.js';
import { BattleSession } from './BattleSession.js';
import { translateMove, translatePokemon } from './translations.js';
import { Canvas, loadImage, FontLibrary } from 'skia-canvas';
import * as path from 'path';
import * as fs from 'fs';
import { getPokemonSpriteAsset } from './pokerogue.js';
import { Sprites } from '@pkmn/img';

let isFontLoaded = false;
function loadZpixFont() {
  if (!isFontLoaded) {
    try {
      const fontPath = path.join(process.cwd(), 'assets/fonts/zpix.ttf');
      FontLibrary.use('Zpix', fontPath);
      const emsFontPath = path.join(process.cwd(), 'assets/fonts/pkmnems.ttf');
      FontLibrary.use('pkmnems', emsFontPath);
      isFontLoaded = true;
      console.log('📝 成功註冊對戰畫面像素字型 Zpix 與 pkmnems');
    } catch (err) {
      console.error('❌ 無法載入對戰像素字型:', err);
    }
  }
}

// 屬性與異常狀態坐標對照
const TYPES_Y_ICON_MAP: Record<string, number> = {
  unknown: 0,
  bug: 12,
  dark: 24,
  dragon: 36,
  electric: 48,
  fairy: 60,
  fighting: 72,
  fire: 84,
  flying: 96,
  ghost: 108,
  grass: 120,
  ground: 132,
  ice: 144,
  normal: 156,
  poison: 168,
  psychic: 180,
  rock: 192,
  steel: 204,
  water: 216,
  stellar: 228
};

const STATUS_Y_MAP: Record<string, { y: number; w: number; h: number }> = {
  brn: { y: 8, w: 20, h: 8 },      // burn
  frz: { y: 24, w: 20, h: 8 },     // freeze
  par: { y: 32, w: 20, h: 8 },     // paralysis
  psn: { y: 40, w: 20, h: 8 },     // poison
  slp: { y: 48, w: 20, h: 8 },     // sleep
  tox: { y: 56, w: 20, h: 8 }      // toxic
};

// 快取大圖
let typesImg: any = null;
let statusImg: any = null;
let bgForestImg: any = null;
let hudPlayer: any = null;
let hudEnemy: any = null;
let windowImg: any = null;
let playerType1Img: any = null;
let playerType2Img: any = null;
let enemyType1Img: any = null;
let enemyType2Img: any = null;
let iconTeraImg: any = null;
let iconMegaImg: any = null;

async function loadCommonAssets() {
  if (!typesImg) {
    typesImg = await loadImage(path.join(process.cwd(), 'assets/types_zh-Hant.png'));
  }
  if (!statusImg) {
    statusImg = await loadImage(path.join(process.cwd(), 'assets/statuses_zh-Hant.png'));
  }
  if (!bgForestImg) {
    bgForestImg = await loadImage(path.join(process.cwd(), 'assets/bg-forest.png'));
  }
  if (!hudPlayer) {
    hudPlayer = await loadImage(path.join(process.cwd(), 'assets/pbinfo_player.png'));
  }
  if (!hudEnemy) {
    hudEnemy = await loadImage(path.join(process.cwd(), 'assets/pbinfo_enemy_mini.png'));
  }
  if (!windowImg) {
    windowImg = await loadImage(path.join(process.cwd(), 'assets/window_1.png'));
  }
  if (!playerType1Img) {
    playerType1Img = await loadImage(path.join(process.cwd(), 'assets/pbinfo_player_type1.png'));
  }
  if (!playerType2Img) {
    playerType2Img = await loadImage(path.join(process.cwd(), 'assets/pbinfo_player_type2.png'));
  }
  if (!enemyType1Img) {
    enemyType1Img = await loadImage(path.join(process.cwd(), 'assets/pbinfo_enemy_type1.png'));
  }
  if (!enemyType2Img) {
    enemyType2Img = await loadImage(path.join(process.cwd(), 'assets/pbinfo_enemy_type2.png'));
  }
  if (!iconTeraImg) {
    iconTeraImg = await loadImage(path.join(process.cwd(), 'assets/icon_tera.png'));
  }
  if (!iconMegaImg) {
    iconMegaImg = await loadImage(path.join(process.cwd(), 'assets/icon_mega.png'));
  }
}

/**
 * 繪製漂亮的 HP 進度條 (Discord Embed)
 */
function makeHpBar(percent: number): string {
  const totalBars = 10;
  const filledBars = Math.max(0, Math.min(totalBars, Math.round((percent / 100) * totalBars)));
  const emptyBars = totalBars - filledBars;
  
  let colorEmoji = '🟩'; // 綠色
  if (percent <= 20) {
    colorEmoji = '🟥'; // 紅色
  } else if (percent <= 50) {
    colorEmoji = '🟨'; // 黃色
  }
  
  return colorEmoji.repeat(filledBars) + '⬛'.repeat(emptyBars);
}

/**
 * 取得寶可夢的 GIF 圖片連結 (使用 @pkmn/img)
 */
function getPokemonSpriteUrl(species: string): string {
  try {
    const sprite = Sprites.getPokemon(species, { gen: 'ani' });
    return sprite.url || '';
  } catch {
    return `https://play.pokemonshowdown.com/sprites/ani/${species.toLowerCase().replace(/[^a-z0-9-]/g, '')}.gif`;
  }
}

/**
 * 1. 繪製公開頻道的對戰看板 (Embed)
 */
export function renderBattleEmbed(session: BattleSession, lastLogs: string): EmbedBuilder {
  const state = session.getBattleState();
  const p1Sprite = getPokemonSpriteUrl(session.battle.p1.active[0]?.species.id || 'pikachu');
  
  const embed = new EmbedBuilder()
    .setTitle('⚔️ 寶可夢 Champions 對戰擂台')
    .setDescription(`**目前回合：第 ${session.battle.turn} 回合**`)
    .setColor(session.isEnded() ? 0x00FF00 : 0xFF0000)
    .addFields(
      {
        name: `🔴 挑戰者：${state.p1.name}`,
        value: `场上精靈: **${state.p1.activeName}**\nHP: **${state.p1.hp}/${state.p1.maxhp}** (${state.p1.hpPercent}%)\n${makeHpBar(state.p1.hpPercent)}`,
        inline: true
      },
      {
        name: `🔵 被挑戰者：${state.p2.name}`,
        value: `场上精靈: **${state.p2.activeName}**\nHP: **${state.p2.hp}/${state.p2.maxhp}** (${state.p2.hpPercent}%)\n${makeHpBar(state.p2.hpPercent)}`,
        inline: true
      }
    );

  if (session.isEnded()) {
    const winner = session.getWinner();
    embed.addFields({
      name: '🏆 對戰結束',
      value: winner ? `🎉 **恭喜 ${winner.name} 贏得了這場勝利！**` : '🤝 這場對戰打成了平手！',
      inline: false
    });
  } else {
    embed.addFields({
      name: '📝 對戰即時快訊',
      value: lastLogs.trim() || '*對戰開始！雙方已派出第一隻寶可夢，請玩家做出抉擇。*',
      inline: false
    });
  }

  if (p1Sprite) {
    embed.setThumbnail(p1Sprite);
  }

  embed.setFooter({ text: 'Pokémon Champions VGC Mode | Powered by @pkmn/sim' });
  return embed;
}

/**
 * 2. 繪製玩家個人的私密出招手把 (Buttons)
 */
export function renderBattleButtons(
  session: BattleSession,
  playerNum: 'p1' | 'p2',
  state: { isMegaOn: boolean; isTeraOn: boolean; selectedMoveIdx: number | null }
) {
  const req = session.getPlayerRequest(playerNum);
  const rows: ActionRowBuilder<any>[] = [];

  if (req.type === 'wait') {
    const row = new ActionRowBuilder<ButtonBuilder>().addComponents(
      new ButtonBuilder()
        .setCustomId('wait_btn')
        .setLabel('⏳ 等待對手決定中...')
        .setStyle(ButtonStyle.Secondary)
        .setDisabled(true)
    );
    rows.push(row);
    return rows;
  }

  if (req.type === 'switch') {
    const eligible = (req as any).eligiblePokemons || [];
    
    if (eligible.length > 0) {
      const selectMenu = new StringSelectMenuBuilder()
        .setCustomId(`battle_switch_select_${playerNum}`)
        .setPlaceholder('選擇一隻後備寶可夢換上場')
        .addOptions(
          eligible.map((p: any) => ({
            label: `${translatePokemon(p.name)} (HP: ${Math.ceil((p.hp/p.maxhp)*100)}%)`,
            value: `switch ${p.index}`,
            description: p.fainted ? '已瀕死' : '健康狀態'
          }))
        );
      
      const row = new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(selectMenu);
      rows.push(row);
    } else {
      const row = new ActionRowBuilder<ButtonBuilder>().addComponents(
        new ButtonBuilder()
          .setCustomId('no_switch_btn')
          .setLabel('💀 無法替換，等待對戰結算')
          .setStyle(ButtonStyle.Danger)
          .setDisabled(true)
      );
      rows.push(row);
    }
    return rows;
  }

  if (req.type === 'move') {
    const moveReq = req as any;
    const moveRow = new ActionRowBuilder<ButtonBuilder>();
    moveReq.moves.forEach((move: any) => {
      const isSelected = state.selectedMoveIdx === move.index;
      moveRow.addComponents(
        new ButtonBuilder()
          .setCustomId(`battle_move_${playerNum}_${move.index}`)
          .setLabel(`${translateMove(move.name)} (PP: ${move.pp}/${move.maxpp})`)
          .setStyle(isSelected ? ButtonStyle.Success : ButtonStyle.Primary)
          .setDisabled(!!move.disabled)
      );
    });
    rows.push(moveRow);

    const systemRow = new ActionRowBuilder<ButtonBuilder>();
    let hasSystemButtons = false;

    if (moveReq.canMega) {
      systemRow.addComponents(
        new ButtonBuilder()
          .setCustomId(`battle_mega_toggle_${playerNum}`)
          .setLabel(state.isMegaOn ? '🟢 Mega進化：開啟' : '⚫ Mega進化：關閉')
          .setStyle(state.isMegaOn ? ButtonStyle.Success : ButtonStyle.Secondary)
      );
      hasSystemButtons = true;
    }

    if (moveReq.canTera) {
      systemRow.addComponents(
        new ButtonBuilder()
          .setCustomId(`battle_tera_toggle_${playerNum}`)
          .setLabel(state.isTeraOn ? '🟢 太晶化：開啟' : '⚫ 太晶化：關閉')
          .setStyle(state.isTeraOn ? ButtonStyle.Success : ButtonStyle.Secondary)
      );
      hasSystemButtons = true;
    }

    if (hasSystemButtons) {
      rows.push(systemRow);
    }

    const switchEligible = moveReq.eligiblePokemons || [];
    if (switchEligible.length > 0) {
      const selectMenu = new StringSelectMenuBuilder()
        .setCustomId(`battle_switch_select_${playerNum}`)
        .setPlaceholder('🔄 或是選擇更換後備寶可夢')
        .addOptions(
          switchEligible.map((p: any) => ({
            label: `${translatePokemon(p.name)} (HP: ${Math.ceil((p.hp/p.maxhp)*100)}%)`,
            value: `switch ${p.index}`,
            description: '替換當前場上寶可夢'
          }))
        );
      
      const switchRow = new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(selectMenu);
      rows.push(switchRow);
    }

    if (state.selectedMoveIdx !== null) {
      const submitRow = new ActionRowBuilder<ButtonBuilder>().addComponents(
        new ButtonBuilder()
          .setCustomId(`battle_submit_action_${playerNum}`)
          .setLabel('🚀 確認出招！')
          .setStyle(ButtonStyle.Danger)
      );
      rows.push(submitRow);
    }
  }

  return rows;
}

/**
 * 繪製一個圓角矩形 (輔助函數)
 */
function drawRoundRect(
  ctx: any,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

function drawPixelTextWithStroke(
  ctx: any,
  text: string,
  x: number,
  y: number,
  textColor: string,
  strokeColor: string = '#000000',
  thickness: number = 3
) {
  ctx.save();
  ctx.fillStyle = strokeColor;
  const offset = Math.max(1, Math.round(thickness / 1.5));
  
  ctx.fillText(text, x - offset, y - offset);
  ctx.fillText(text, x, y - offset);
  ctx.fillText(text, x + offset, y - offset);
  ctx.fillText(text, x - offset, y);
  ctx.fillText(text, x + offset, y);
  ctx.fillText(text, x - offset, y + offset);
  ctx.fillText(text, x, y + offset);
  ctx.fillText(text, x + offset, y + offset);
  
  ctx.fillStyle = textColor;
  ctx.fillText(text, x, y);
  ctx.restore();
}

/**
 * 使用九宮格拉伸法繪製對話框 (window_1.png 專用，3倍放大)
 */
function drawWindow(
  ctx: any,
  windowImg: any,
  dx: number,
  dy: number,
  dw: number,
  dh: number
) {
  const sCorner = 8;
  const sCenter = 8;
  const dCorner = 24; // 8 * 3

  ctx.imageSmoothingEnabled = false;

  // 1. 四個角
  ctx.drawImage(windowImg, 0, 0, sCorner, sCorner, dx, dy, dCorner, dCorner); // 左上
  ctx.drawImage(windowImg, 16, 0, sCorner, sCorner, dx + dw - dCorner, dy, dCorner, dCorner); // 右上
  ctx.drawImage(windowImg, 0, 16, sCorner, sCorner, dx, dy + dh - dCorner, dCorner, dCorner); // 左下
  ctx.drawImage(windowImg, 16, 16, sCorner, sCorner, dx + dw - dCorner, dy + dh - dCorner, dCorner, dCorner); // 右下

  // 2. 四個邊
  ctx.drawImage(windowImg, 8, 0, sCenter, sCorner, dx + dCorner, dy, dw - 2 * dCorner, dCorner); // 上
  ctx.drawImage(windowImg, 8, 16, sCenter, sCorner, dx + dCorner, dy + dh - dCorner, dw - 2 * dCorner, dCorner); // 下
  ctx.drawImage(windowImg, 0, 8, sCorner, sCenter, dx, dy + dCorner, dCorner, dh - 2 * dCorner); // 左
  ctx.drawImage(windowImg, 16, 8, sCorner, sCenter, dx + dw - dCorner, dy + dCorner, dCorner, dh - 2 * dCorner); // 右

  // 3. 中心填充
  ctx.drawImage(windowImg, 8, 8, sCenter, sCenter, dx + dCorner, dy + dCorner, dw - 2 * dCorner, dh - 2 * dCorner);
}

/**
 * 繪製單個狀態徽章 (3倍像素大小：60x24)
 */
function drawStatusBadge(ctx: any, statusName: string, dx: number, dy: number) {
  const statusKey = statusName.toLowerCase().trim();
  const info = STATUS_Y_MAP[statusKey];
  if (!info) return;

  const tempCanvas = new Canvas(info.w, info.h);
  const tempCtx = tempCanvas.getContext('2d');
  tempCtx.drawImage(statusImg, 0, -info.y);

  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(tempCanvas, dx, dy, 60, 24);
}

/**
 * 繪製 PokéRogue 官方原裝屬性圖示 (2倍放大：40x24)
 * @param isType2 是否為雙屬性的第一屬性 (左邊積木)
 */
function drawPokeRogueTypeBadge(
  ctx: any,
  typeName: string,
  dx: number,
  dy: number,
  isPlayer: boolean,
  isType2: boolean
) {
  const typeKey = typeName.toLowerCase().trim();
  const yOffset = TYPES_Y_ICON_MAP[typeKey];
  if (yOffset === undefined) return;

  const tempCanvas = new Canvas(20, 12);
  const tempCtx = tempCanvas.getContext('2d');
  
  // 根據角色與積木位置選取對應貼圖
  let img = isPlayer 
    ? (isType2 ? playerType2Img : playerType1Img)
    : (isType2 ? enemyType2Img : enemyType1Img);

  tempCtx.drawImage(img, 0, -yOffset);

  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(tempCanvas, dx, dy, 80, 48);
}

/**
 * 繪製精美的寶可夢資訊 HUD (HP 狀態條與資訊框，無等級與經驗值)
 */
function drawPokemonHUD(
  ctx: any,
  hudBg: any,
  isPlayer: boolean,
  x: number,
  y: number,
  name: string,
  level: number,
  hp: number,
  maxHp: number,
  gender: string,
  types: string[],
  status: string,
  isTera: boolean = false,
  isMega: boolean = false
) {
  const hpPercent = Math.max(0, Math.min(100, Math.round((hp / maxHp) * 100)));
  const w = 390;
  const h = 84; // 框高度設為 84px，配合 4 倍屬性徽章重疊 12px 完美貼合
  const xOffset = isPlayer ? 80 : 0; // 我方屬性在左佔用 80px，主體往右移 80px；敵方主體在左，屬性在右
  
  // 1. 繪製六邊形底板
  ctx.save();
  ctx.shadowColor = 'rgba(0, 0, 0, 0.35)';
  ctx.shadowBlur = 8;
  ctx.shadowOffsetX = 3;
  ctx.shadowOffsetY = 3;
  
  ctx.fillStyle = '#2c2438';
  ctx.beginPath();
  
  if (isPlayer) {
    // 我方屬性在左側：左側對接 100% 貼合 4 倍徽章右邊緣的階梯折線（向左擴展 1 像素防抗鋸齒透光）
    ctx.moveTo(x + 71, y);
    ctx.lineTo(x + 71, y + 8);
    ctx.lineTo(x + 75, y + 8);
    ctx.lineTo(x + 75, y + 24);
    ctx.lineTo(x + 79, y + 24);
    ctx.lineTo(x + 79, y + h);
    // 右側外邊界六邊形尖角（中點 y + 42 處突出，斜切量為 24px 以修飾角度）
    ctx.lineTo(x + w - 24, y + h);
    ctx.lineTo(x + w, y + 42);
    ctx.lineTo(x + w - 24, y);
  } else {
    // 敵方屬性在右側：右側對接 100% 貼合 4 倍徽章左邊緣的階梯折線（向右擴展 1 像素防抗鋸齒透光）
    ctx.moveTo(x + 24, y); // 左側斜切量為 24px 以修飾角度
    ctx.lineTo(x + w - 71, y);
    ctx.lineTo(x + w - 71, y + 8);
    ctx.lineTo(x + w - 75, y + 8);
    ctx.lineTo(x + w - 75, y + 24);
    ctx.lineTo(x + w - 79, y + 24);
    ctx.lineTo(x + w - 79, y + h);
    // 左側外邊界六邊形尖角（中點 y + 42 處突出）
    ctx.lineTo(x + 24, y + h);
    ctx.lineTo(x, y + 42);
  }
  
  ctx.closePath();
  ctx.fill();
  ctx.restore();
  
  // 3. 繪製寶可夢名稱、性別、特殊進化/屬性 UI 圖示
  ctx.save();
  ctx.font = '16px Zpix';
  
  let displayName = name;
  let startX = x + xOffset + 24;
  // 3.1 繪製寶可夢名稱 (平移至上方 y + 28，留白適中)
  drawPixelTextWithStroke(ctx, displayName, startX, y + 28, '#FFFFFF', '#000000', 3);
  const nameWidth = ctx.measureText(displayName).width;
  
  // 3.2 繪製性別
  let genderX = startX + nameWidth + 6;
  let genderWidth = 0;
  if (gender === 'M') {
    ctx.font = '15px Zpix';
    drawPixelTextWithStroke(ctx, '♂', genderX, y + 27, '#5dade2', '#000000', 3);
    genderWidth = ctx.measureText('♂').width;
  } else if (gender === 'F') {
    ctx.font = '15px Zpix';
    drawPixelTextWithStroke(ctx, '♀', genderX, y + 27, '#f48fb1', '#000000', 3);
    genderWidth = ctx.measureText('♀').width;
  }
  
  // 3.3 繪製特殊進化/屬性 UI 圖示在性別右邊 (對齊 y + 16 附近以防重疊)
  const specialX = genderX + genderWidth + (genderWidth > 0 ? 8 : 4);
  if (isTera && iconTeraImg) {
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(iconTeraImg, specialX, y + 16, 16, 20); // 16x20 字高對齊
  } else if (isMega && iconMegaImg) {
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(iconMegaImg, specialX, y + 18, 16, 16); // 16x16 比例對齊
  }
  ctx.restore();
  
  // 4. 繪製屬性徽章
  if (types && types.length > 0) {
    const typeY1 = y;       // 上方第一屬性 (y 到 y + 48)
    const typeY2 = y + 36;  // 下方第二屬性 (y + 36 到 y + 84)，重疊 12px 完美貼合
    let drawX1 = 0;
    let drawX2 = 0;
    
    if (isPlayer) {
      drawX1 = x;
      drawX2 = x;
    } else {
      drawX1 = x + w - 80;
      drawX2 = x + w - 80;
    }
    
    if (types.length === 1) {
      drawPokeRogueTypeBadge(ctx, types[0], drawX1, typeY1, isPlayer, false);
    } else if (types.length >= 2) {
      drawPokeRogueTypeBadge(ctx, types[0], drawX1, typeY1, isPlayer, false);
      drawPokeRogueTypeBadge(ctx, types[1], drawX2, typeY2, isPlayer, true);
    }
  }
  
  // 5. 繪製血條
  const barX = x + xOffset + 145;
  const barY = y + 38; // 下移至 y + 38，居中舒展
  const barW = 150;
  const barH = 10; // 保持 10px 高度
  const barSkew = 3;
  
  ctx.save();
  ctx.fillStyle = '#000000';
  ctx.beginPath();
  ctx.moveTo(barX + barSkew, barY - 1.5);
  ctx.lineTo(barX + barW + barSkew, barY - 1.5);
  ctx.lineTo(barX + barW, barY + barH + 1.5);
  ctx.lineTo(barX, barY + barH + 1.5);
  ctx.closePath();
  ctx.fill();
  
  ctx.fillStyle = '#222222';
  ctx.beginPath();
  ctx.moveTo(barX + barSkew, barY);
  ctx.lineTo(barX + barW, barY);
  ctx.lineTo(barX + barW - barSkew, barY + barH);
  ctx.lineTo(barX, barY + barH);
  ctx.closePath();
  ctx.fill();
  
  if (hpPercent > 0) {
    const rawBarW = (hpPercent / 100) * (barW - barSkew);
    const hpBarW = Math.max(3, Math.round(rawBarW / 3) * 3);
    
    ctx.beginPath();
    ctx.moveTo(barX + barSkew, barY);
    ctx.lineTo(barX + barSkew + hpBarW, barY);
    ctx.lineTo(barX + hpBarW, barY + barH);
    ctx.lineTo(barX, barY + barH);
    ctx.closePath();
    ctx.clip();
    
    let colors = { light: '#84fa94', main: '#3cc060', dark: '#188828' };
    if (hpPercent <= 20) colors = { light: '#f85838', main: '#d02000', dark: '#900000' };
    else if (hpPercent <= 50) colors = { light: '#f8d030', main: '#e0a000', dark: '#a87000' };
    
    ctx.fillStyle = colors.light;
    ctx.fillRect(barX - 10, barY, barW + 20, 3.5);
    ctx.fillStyle = colors.main;
    ctx.fillRect(barX - 10, barY + 3.5, barW + 20, 3.5);
    ctx.fillStyle = colors.dark;
    ctx.fillRect(barX - 10, barY + 7, barW + 20, 3);
  }
  ctx.restore();
  
  // 6. 狀態徽章與 HP 數值
  ctx.save();
  if (status) drawStatusBadge(ctx, status, x + xOffset + 24, y + 38); // 狀態徽章移至 y + 38，與血條完美水平對齊
  if (isPlayer) {
    ctx.font = '12px Zpix';
    ctx.textAlign = 'right';
    drawPixelTextWithStroke(ctx, `${hp}/${maxHp}`, x + xOffset + 300, y + 68, '#ffffff', '#000000', 2); // HP 數值平移至下半部偏下 y + 68
  }
  ctx.restore();
}

/**
 * 繪製 2D 像素精靈 (解析 JSON 第一幀並繪製，腳底對齊 dy，水平居中於 dx)
 */
function drawPokemonSprite(
  ctx: any,
  img: any,
  json: any,
  dx: number,
  dy: number,
  scale: number = 3
) {
  const frameInfo = json.textures[0].frames[0].frame;
  const { x, y, w, h } = frameInfo;

  const tempCanvas = new Canvas(w, h);
  const tempCtx = tempCanvas.getContext('2d');
  tempCtx.drawImage(img, -x, -y);

  const drawW = w * scale;
  const drawH = h * scale;
  const drawX = dx - drawW / 2;
  const drawY = dy - drawH;

  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(tempCanvas, drawX, drawY, drawW, drawH);
}

/**
 * 繪製對戰天氣徽章
 */
function drawWeatherBadge(ctx: any, weatherName: string) {
  ctx.save();
  ctx.fillStyle = 'rgba(255, 165, 0, 0.85)';
  ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
  ctx.shadowBlur = 5;
  drawRoundRect(ctx, 420, 20, 120, 30, 15);
  ctx.fill();
  
  ctx.fillStyle = '#FFFFFF';
  ctx.font = '12px pkmnems, Zpix';
  ctx.fillText(`☀️ 天氣：${weatherName}`, 428, 39);
  ctx.restore();
}

function translateWeatherName(weather: string): string {
  const w = weather.toLowerCase();
  if (w.includes('sun') || w.includes('sunny') || w.includes('clear')) return '大晴天';
  if (w.includes('rain')) return '下雨天';
  if (w.includes('sand')) return '沙暴';
  if (w.includes('hail') || w.includes('snow')) return '冰雪天';
  return '無天氣';
}

/**
 * 核心 Canvas 渲染對戰畫面 (完全使用 PokéRogue 2D 像素美術，960x540)
 */
export async function generateBattleImage(session: BattleSession, lastLogs: string = ''): Promise<Buffer> {
  loadZpixFont();
  await loadCommonAssets();

  const state = session.getBattleState();
  const canvas = new Canvas(960, 540);
  const ctx = canvas.getContext('2d');

  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(bgForestImg, 0, 0, 960, 540);

  if (state.terrain) {
    drawTerrainOverlay(ctx, state.terrain);
  }

  if (!state.p1.fainted) {
    try {
      const p1Species = session.battle.p1.active[0]?.species.id || 'pikachu';
      const p1Asset = await getPokemonSpriteAsset(p1Species, true);
      const p1Img = await loadImage(p1Asset.imagePath);
      const p1Json = JSON.parse(fs.readFileSync(p1Asset.jsonPath, 'utf8'));
      drawPokemonSprite(ctx, p1Img, p1Json, 270, 480, 3.0);
    } catch (err) {
      console.error('無法載入我方精靈圖片，繪製佔位圓形:', err);
      ctx.fillStyle = '#e67e22';
      ctx.beginPath();
      ctx.arc(270, 420, 80, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  if (!state.p2.fainted) {
    try {
      const p2Species = session.battle.p2.active[0]?.species.id || 'charizard';
      const p2Asset = await getPokemonSpriteAsset(p2Species, false);
      const p2Img = await loadImage(p2Asset.imagePath);
      const p2Json = JSON.parse(fs.readFileSync(p2Asset.jsonPath, 'utf8'));
      drawPokemonSprite(ctx, p2Img, p2Json, 690, 330, 3.0);
    } catch (err) {
      console.error('無法載入敵方精靈圖片，繪製佔位圓形:', err);
      ctx.fillStyle = '#f1c40f';
      ctx.beginPath();
      ctx.arc(690, 280, 60, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // 敵方 HUD (左上方, x=10, y=15)
  if (!state.p2.fainted) {
    drawPokemonHUD(
      ctx,
      null,
      false,
      10,
      15,
      state.p2.activeName,
      state.p2.level,
      state.p2.hp,
      state.p2.maxhp,
      state.p2.gender,
      state.p2.types,
      state.p2.status,
      state.p2.isTera,
      state.p2.isMega
    );
  }

  // 我方 HUD (右下方, x=560, y=420)
  if (!state.p1.fainted) {
    drawPokemonHUD(
      ctx,
      null,
      true,
      560,
      420,
      state.p1.activeName,
      state.p1.level,
      state.p1.hp,
      state.p1.maxhp,
      state.p1.gender,
      state.p1.types,
      state.p1.status,
      state.p1.isTera,
      state.p1.isMega
    );
  }

  if (state.weather) {
    drawWeatherBadge(ctx, translateWeatherName(state.weather));
  }

  if (state.weather) {
    drawWeatherOverlay(ctx, state.weather);
  }

  return canvas.toBuffer('png');
}

/**
 * 繪製天氣的 Canvas 特效疊加 (晴天光芒、雨絲、沙暴飛沙、雪花)
 */
function drawWeatherOverlay(ctx: any, weather: string) {
  const w = weather.toLowerCase();
  
  if (w.includes('sun') || w.includes('sunny') || w.includes('clear')) {
    ctx.save();
    const grad = ctx.createLinearGradient(0, 0, 0, 180);
    grad.addColorStop(0, 'rgba(255, 223, 0, 0.15)');
    grad.addColorStop(1, 'rgba(255, 223, 0, 0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 960, 540);
    
    ctx.fillStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.beginPath();
    ctx.moveTo(0, 0); ctx.lineTo(200, 0); ctx.lineTo(500, 540); ctx.lineTo(250, 540);
    ctx.closePath(); ctx.fill();
    
    ctx.beginPath();
    ctx.moveTo(400, 0); ctx.lineTo(550, 0); ctx.lineTo(960, 540); ctx.lineTo(750, 540);
    ctx.closePath(); ctx.fill();
    ctx.restore();
  }
  
  if (w.includes('rain')) {
    ctx.save();
    ctx.strokeStyle = 'rgba(174, 219, 240, 0.35)';
    ctx.lineWidth = 1.5;
    for (let i = 0; i < 80; i++) {
      const rx = Math.random() * 1100 - 100;
      const ry = Math.random() * 540;
      ctx.beginPath();
      ctx.moveTo(rx, ry);
      ctx.lineTo(rx + 12, ry + 36);
      ctx.stroke();
    }
    ctx.restore();
  }
  
  if (w.includes('sand')) {
    ctx.save();
    ctx.fillStyle = 'rgba(190, 140, 80, 0.15)';
    ctx.fillRect(0, 0, 960, 540);
    
    ctx.strokeStyle = 'rgba(230, 180, 110, 0.45)';
    ctx.lineWidth = 2;
    for (let i = 0; i < 60; i++) {
      const rx = Math.random() * 960;
      const ry = Math.random() * 540;
      const len = Math.random() * 20 + 15;
      ctx.beginPath();
      ctx.moveTo(rx, ry);
      ctx.lineTo(rx + len, ry + (Math.random() * 4 - 2));
      ctx.stroke();
    }
    ctx.restore();
  }
  
  if (w.includes('hail') || w.includes('snow')) {
    ctx.save();
    for (let i = 0; i < 80; i++) {
      const rx = Math.random() * 960;
      const ry = Math.random() * 540;
      const size = Math.random() * 3 + 1.5;
      
      ctx.beginPath();
      ctx.fillStyle = `rgba(255, 255, 255, ${Math.random() * 0.5 + 0.45})`;
      ctx.arc(rx, ry, size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }
}

/**
 * 繪製精靈腳下的場地效果發光圈 (青草、電氣、精神、薄霧)
 */
function drawTerrainOverlay(ctx: any, terrain: string) {
  const t = terrain.toLowerCase();
  if (!t) return;
  
  const spots = [
    { cx: 270, cy: 444, rx: 132, ry: 48 },
    { cx: 690, cy: 360, rx: 90, ry: 30 }
  ];
  
  ctx.save();
  
  spots.forEach(spot => {
    if (t.includes('grass')) {
      const grad = ctx.createRadialGradient(spot.cx, spot.cy, 5, spot.cx, spot.cy, spot.rx);
      grad.addColorStop(0, 'rgba(46, 204, 113, 0.55)');
      grad.addColorStop(0.6, 'rgba(39, 174, 96, 0.35)');
      grad.addColorStop(1, 'rgba(39, 174, 96, 0)');
      
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.ellipse(spot.cx, spot.cy, spot.rx, spot.ry, 0, 0, Math.PI * 2);
      ctx.fill();
      
      ctx.fillStyle = '#AEEB00';
      for (let i = 0; i < 8; i++) {
        const lx = spot.cx + (Math.random() * spot.rx * 2 - spot.rx) * 0.7;
        const ly = spot.cy + (Math.random() * spot.ry * 2 - spot.ry) * 0.7;
        ctx.beginPath();
        ctx.arc(lx, ly, 3.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    
    if (t.includes('electric')) {
      const grad = ctx.createRadialGradient(spot.cx, spot.cy, 5, spot.cx, spot.cy, spot.rx);
      grad.addColorStop(0, 'rgba(241, 196, 15, 0.65)');
      grad.addColorStop(0.6, 'rgba(243, 156, 18, 0.4)');
      grad.addColorStop(1, 'rgba(243, 156, 18, 0)');
      
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.ellipse(spot.cx, spot.cy, spot.rx, spot.ry, 0, 0, Math.PI * 2);
      ctx.fill();
      
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.8;
      for (let i = 0; i < 4; i++) {
        const startX = spot.cx + (Math.random() * spot.rx - spot.rx / 2);
        const startY = spot.cy - 12;
        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.lineTo(startX + (Math.random() * 8 - 4), startY + 6);
        ctx.lineTo(startX + (Math.random() * 8 - 4), startY + 12);
        ctx.stroke();
      }
    }
    
    if (t.includes('psychic')) {
      const grad = ctx.createRadialGradient(spot.cx, spot.cy, 5, spot.cx, spot.cy, spot.rx);
      grad.addColorStop(0, 'rgba(155, 89, 182, 0.65)');
      grad.addColorStop(0.6, 'rgba(142, 68, 173, 0.4)');
      grad.addColorStop(1, 'rgba(142, 68, 173, 0)');
      
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.ellipse(spot.cx, spot.cy, spot.rx, spot.ry, 0, 0, Math.PI * 2);
      ctx.fill();
      
      ctx.strokeStyle = 'rgba(255, 120, 255, 0.65)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.ellipse(spot.cx, spot.cy, spot.rx * 0.7, spot.ry * 0.7, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    
    if (t.includes('misty')) {
      const grad = ctx.createRadialGradient(spot.cx, spot.cy, 5, spot.cx, spot.cy, spot.rx);
      grad.addColorStop(0, 'rgba(253, 221, 230, 0.75)');
      grad.addColorStop(0.6, 'rgba(244, 143, 177, 0.4)');
      grad.addColorStop(1, 'rgba(244, 143, 177, 0)');
      
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.ellipse(spot.cx, spot.cy, spot.rx, spot.ry, 0, 0, Math.PI * 2);
      ctx.fill();
    }
  });
  
  ctx.restore();
}
