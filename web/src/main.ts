import '../../game/styles.css';
import './legacy';
import { SurvivalGame } from './game';

const canvas=document.getElementById('world');
if(!(canvas instanceof HTMLCanvasElement))throw new Error('Game canvas is missing');
try {
  const game=new SurvivalGame(canvas);
  game.initialize().catch(error=>{
    console.error('[RAFTBOUND] Initialization failed',error);
    document.getElementById('assetStatus')!.textContent='Lỗi khởi tạo asset / vật lý';
  });
} catch(error){
  console.error('[RAFTBOUND] WebGL initialization failed',error);
  document.getElementById('startOverlay')!.innerHTML='<div class="intro-card"><h1>Không thể chạy WebGL</h1><p>Hãy sử dụng trình duyệt hỗ trợ WebGL2 và tăng tốc phần cứng.</p></div>';
}
