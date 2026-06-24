import { Canvas, loadImage, FontLibrary } from 'skia-canvas';
import * as fs from 'fs';
import * as path from 'path';

// 1. 註冊 Zpix 與 pkmnems 像素字型
const fontPath = path.join(process.cwd(), 'assets/fonts/zpix.ttf');
FontLibrary.use('Zpix', fontPath);
const emsFontPath = path.join(process.cwd(), 'assets/fonts/pkmnems.ttf');
FontLibrary.use('pkmnems', emsFontPath);

// 2. 屬性圖示在直排大圖中的 y 坐標映射 (高 12 像素)
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

// 3. 異常狀態 y 坐標與寬高映射 (對照 statuses_zh-Hant.json)
const STATUS_Y_MAP: Record<string, { y: number; w: number; h: number }> = {
  brn: { y: 8, w: 20, h: 8 },      // burn
  frz: { y: 24, w: 20, h: 8 },     // freeze
  par: { y: 32, w: 20, h: 8 },     // paralysis
  psn: { y: 40, w: 20, h: 8 },     // poison
  slp: { y: 48, w: 20, h: 8 },     // sleep
  tox: { y: 56, w: 20, h: 8 }      // toxic
};

let typesImg: any = null;
let statusImg: any = null;
let playerType1Img: any = null;
let playerType2Img: any = null;
let enemyType1Img: any = null;
let enemyType2Img: any = null;
let iconTeraImg: any = null;
let iconMegaImg: any = null;

// 4. 輔助函數：繪製圓角矩形
function drawRoundRect(ctx: any, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
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
  
  // 對於 Zpix 等像素字型，使用四/八方向偏移繪製硬像素描邊（厚度 3px -> 偏移 2px)
  const offset = Math.max(1, Math.round(thickness / 1.5));
  
  // 八個方向偏移填充
  ctx.fillText(text, x - offset, y - offset);
  ctx.fillText(text, x, y - offset);
  ctx.fillText(text, x + offset, y - offset);
  ctx.fillText(text, x - offset, y);
  ctx.fillText(text, x + offset, y);
  ctx.fillText(text, x - offset, y + offset);
  ctx.fillText(text, x, y + offset);
  ctx.fillText(text, x + offset, y + offset);
  
  // 主體文字
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
 * 繪製精美的寶可夢資訊 HUD (HP 狀態條與資訊框，無等級與經驗值)
 */
function drawPokemonHUD(
  ctx: any,
  hudBg: any, // 為了相容性保留此參數
  isPlayer: boolean,
  x: number,
  y: number,
  name: string,
  level: number,       // 保留相容性，但不再繪製
  hp: number,
  maxHp: number,
  gender: string,      // 'M' | 'F' | ''
  types: string[],     // 屬性陣列
  status: string,      // 'slp' | 'brn'
  isTera: boolean = false,
  isMega: boolean = false
) {
  const hpPercent = Math.max(0, Math.min(100, Math.round((hp / maxHp) * 100)));
  const w = 390;
  const h = 72; // 框高度設為 72px，配合 4 倍屬性徽章重疊 24px 完美貼合
  const xOffset = isPlayer ? 80 : 0; // 我方屬性在左佔用 80px，主體往右移 80px
  
  // 1. 先繪製屬性徽章 (在底板下方，這樣底底框的黑色邊框可以壓在屬性上層，遮蓋其邊緣透明塊)
  if (types && types.length > 0) {
    const typeY1 = y;       // 上方第一屬性 (y 到 y + 48)
    const typeY2 = y + 24;  // 下方第二屬性 (y + 24 到 y + 72)，重疊 24px 完美貼合 72px
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

  // 2. 繪製六邊形底板填充 (壓在屬性徽章上層)
  ctx.save();
  ctx.shadowColor = 'rgba(0, 0, 0, 0.35)';
  ctx.shadowBlur = 8;
  ctx.shadowOffsetX = 3;
  ctx.shadowOffsetY = 3;
  
  ctx.fillStyle = '#2c2438';
  ctx.beginPath();
  
  if (isPlayer) {
    // 我方屬性在左側：左側對接線（向左擴展 1 像素防抗鋸齒透光）
    ctx.moveTo(x + 71, y);
    ctx.lineTo(x + 79, y + 24);
    ctx.lineTo(x + 79, y + h);
    // 右側外邊界六邊形尖角（中點 y + 36 處突出，斜切量為 24px 以修飾角度）
    ctx.lineTo(x + w - 24, y + h);
    ctx.lineTo(x + w, y + 36);
    ctx.lineTo(x + w - 24, y);
  } else {
    // 敵方屬性在右側：右側對接線（向右擴展 1 像素防抗鋸齒透光）
    ctx.moveTo(x + 24, y); // 左側斜切量為 24px
    ctx.lineTo(x + w - 71, y);
    ctx.lineTo(x + w - 79, y + 24);
    ctx.lineTo(x + w - 79, y + h);
    // 左側外邊界六邊形尖角（中點 y + 36 處突出）
    ctx.lineTo(x + 24, y + h);
    ctx.lineTo(x, y + 36);
  }
  
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  // 2.5 繪製黑色粗外邊框 (在最上層，蓋住屬性接縫與邊緣透明角以防破圖)
  ctx.save();
  ctx.lineWidth = 4;
  ctx.strokeStyle = '#000000';
  ctx.beginPath();
  
  if (isPlayer) {
    ctx.moveTo(x + 71, y);
    ctx.lineTo(x + 79, y + 24);
    ctx.lineTo(x + 79, y + h);
    ctx.lineTo(x + w - 24, y + h);
    ctx.lineTo(x + w, y + 36);
    ctx.lineTo(x + w - 24, y);
  } else {
    ctx.moveTo(x + 24, y);
    ctx.lineTo(x + w - 71, y);
    ctx.lineTo(x + w - 79, y + 24);
    ctx.lineTo(x + w - 79, y + h);
    ctx.lineTo(x + 24, y + h);
    ctx.lineTo(x, y + 36);
  }
  
  ctx.closePath();
  ctx.stroke();
  ctx.restore();
  
  // 3. 繪製寶可夢名稱、性別、特殊進化/屬性 UI 圖示
  ctx.save();
  ctx.font = '16px Zpix';
  
  let displayName = name;
  let startX = x + xOffset + 24;
  // 3.1 繪製寶可夢名稱
  drawPixelTextWithStroke(ctx, displayName, startX, y + 24, '#FFFFFF', '#000000', 3);
  const nameWidth = ctx.measureText(displayName).width;
  
  // 3.2 繪製性別
  let genderX = startX + nameWidth + 6;
  let genderWidth = 0;
  if (gender === 'M') {
    ctx.font = '15px Zpix';
    drawPixelTextWithStroke(ctx, '♂', genderX, y + 23, '#5dade2', '#000000', 3);
    genderWidth = ctx.measureText('♂').width;
  } else if (gender === 'F') {
    ctx.font = '15px Zpix';
    drawPixelTextWithStroke(ctx, '♀', genderX, y + 23, '#f48fb1', '#000000', 3);
    genderWidth = ctx.measureText('♀').width;
  }
  
  // 3.3 繪製特殊進化/屬性 UI 圖示在性別右邊
  const specialX = genderX + genderWidth + (genderWidth > 0 ? 8 : 4);
  if (isTera && iconTeraImg) {
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(iconTeraImg, specialX, y + 8, 16, 20);
  } else if (isMega && iconMegaImg) {
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(iconMegaImg, specialX, y + 10, 16, 16);
  }
  ctx.restore();
  
  // 4. 繪製血條
  const barX = x + xOffset + 145;
  const barY = y + 40;
  const barW = 150;
  const barH = 10;
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
  
  // 5. 狀態徽章與 HP 數值
  ctx.save();
  if (status) drawStatusBadge(ctx, status, x + xOffset + 24, y + 33);
  if (isPlayer) {
    ctx.font = '12px Zpix';
    ctx.textAlign = 'right';
    drawPixelTextWithStroke(ctx, `${hp}/${maxHp}`, x + xOffset + 300, y + 62, '#ffffff', '#000000', 2);
  }
  ctx.restore();
}

/**
 * 執行測試渲染
 */
async function testRender() {
  console.log('正在加載素材...');
  
  // 1. 載入本地草原背景圖
  const bgForest = await loadImage(path.join(process.cwd(), 'assets/bg-forest.png'));
  
  // 2. 載入 PokéRogue 屬性與異常狀態大圖
  statusImg = await loadImage(path.join(process.cwd(), 'assets/statuses_zh-Hant.png'));
  typesImg = await loadImage(path.join(process.cwd(), 'assets/types_zh-Hant.png'));
  const windowImg = await loadImage(path.join(process.cwd(), 'assets/window_1.png'));
  playerType1Img = await loadImage(path.join(process.cwd(), 'assets/pbinfo_player_type1.png'));
  playerType2Img = await loadImage(path.join(process.cwd(), 'assets/pbinfo_player_type2.png'));
  enemyType1Img = await loadImage(path.join(process.cwd(), 'assets/pbinfo_enemy_type1.png'));
  enemyType2Img = await loadImage(path.join(process.cwd(), 'assets/pbinfo_enemy_type2.png'));
  iconTeraImg = await loadImage(path.join(process.cwd(), 'assets/icon_tera.png'));
  iconMegaImg = await loadImage(path.join(process.cwd(), 'assets/icon_mega.png'));

  // 3. 載入 2D 像素精靈圖與 JSON
  const p1Img = await loadImage(path.join(process.cwd(), 'assets/3-back.png'));
  const p1Json = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'assets/3-back.json'), 'utf8'));

  const p2Img = await loadImage(path.join(process.cwd(), 'assets/6.png'));
  const p2Json = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'assets/6.json'), 'utf8'));

  const canvas = new Canvas(960, 540);
  const ctx = canvas.getContext('2d');

  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(bgForest, 0, 0, 960, 540);

  // 我方精靈 (妙蛙花背面)
  drawPokemonSprite(ctx, p1Img, p1Json, 270, 480, 3.0);

  // 敵方精靈 (噴火龍正面)
  drawPokemonSprite(ctx, p2Img, p2Json, 690, 330, 3.0);

  // 敵方 HUD (左上方, x=10, y=15)
  drawPokemonHUD(
    ctx,
    null,
    false,
    10,
    15,
    '噴火龍',
    100,
    180,
    297,
    'M',
    ['Fire', 'Flying'],
    'brn',
    false,
    true
  );

  // 我方 HUD (右下方, x=560, y=420)
  drawPokemonHUD(
    ctx,
    null,
    true,
    560,
    420,
    '妙蛙花',
    85,
    300,
    300,
    'F',
    ['Grass', 'Poison'],
    'slp',
    true,
    false
  );

  // 繪製雨天粒子特效
  ctx.save();
  ctx.strokeStyle = 'rgba(174, 219, 240, 0.35)';
  ctx.lineWidth = 1.5;
  for (let i = 0; i < 60; i++) {
    const rx = Math.random() * 1100 - 100;
    const ry = Math.random() * 540;
    ctx.beginPath();
    ctx.moveTo(rx, ry);
    ctx.lineTo(rx + 12, ry + 36);
    ctx.stroke();
  }
  ctx.restore();

  const buffer = await canvas.toBuffer('png');
  const outputPath = path.join(process.cwd(), 'test_output.png');
  fs.writeFileSync(outputPath, buffer);
  console.log(`\n🎉 100% PokéRogue 素材測試圖已成功生成！路徑：${outputPath}`);
}

import { BattleSession } from './battle/BattleSession.js';
import { generateBattleImage } from './battle/BattleUI.js';

async function testRealBattleRender() {
  console.log('\n📥 開始測試真實對戰模擬渲染 (驗證自動下載與戰場繪製)...');
  const playerA = {
    id: 'user_a',
    name: '玩家小智',
    team: `
Venusaur @ Venusaurite
Ability: Overgrow
EVs: 252 HP / 252 SpA / 4 SpD
Modest Nature
- Giga Drain
- Sludge Bomb
- Earth Power
- Synthesis
`
  };
  const playerB = {
    id: 'user_b',
    name: '玩家小茂',
    team: `
Charizard @ Charizardite Y
Ability: Blaze
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
- Flamethrower
- Solar Beam
- Air Slash
- Protect
`
  };

  const session = new BattleSession(playerA, playerB);
  
  // 第一回合：小智 mega 進化妙蛙花，小茂 mega 進化噴火龍
  session.submitChoice('p1', 'move 1 mega');
  session.submitChoice('p2', 'move 1 mega');

  console.log('正在為真實戰鬥生成圖片...');
  const logs = session.getNewLogs();
  const buffer = await generateBattleImage(session, logs);
  const outputPath = path.join(process.cwd(), 'test_output_battle.png');
  fs.writeFileSync(outputPath, buffer);
  console.log(`🎉 真實戰鬥模擬渲染圖已成功生成！路徑：${outputPath}`);
}

async function main() {
  await testRender();
  await testRealBattleRender();
}

main().catch(err => {
  console.error('測試失敗:', err);
});
