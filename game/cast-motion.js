/* RAFTBOUND A06 shared cast timeline, deterministic and independent of frame rate. */
(function (root) {
 'use strict';
 const CAST=Object.freeze({windup:0.20,release:0.38,contact:0.69,returnStart:0.83,end:1.28});
 const clamp=x=>Math.max(0,Math.min(1,x));
 const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
 const mix=(a,b,t)=>a+(b-a)*t;
 function state(time){
  const t=Math.max(0,time), out={time:t,phase:'done',visibleInHand:false,progress:0,throwArm:0,throwElbow:0,spineLean:0};
  if(t<CAST.windup){const k=smooth(t/CAST.windup);out.phase='windup';out.visibleInHand=true;out.throwArm=mix(0,-0.48,k);out.throwElbow=mix(0,-0.46,k);out.spineLean=-.085*k;}
  else if(t<CAST.release){const k=smooth((t-CAST.windup)/(CAST.release-CAST.windup));out.phase='throw';out.visibleInHand=true;out.throwArm=mix(-.48,1.52,k);out.throwElbow=mix(-.46,.20,k);out.spineLean=mix(-.085,.16,k);}
  else if(t<CAST.contact){out.phase='outbound';out.progress=smooth((t-CAST.release)/(CAST.contact-CAST.release));out.throwArm=mix(1.52,1.04,smooth((t-CAST.release)/.31));out.throwElbow=.20;out.spineLean=.12;}
  else if(t<CAST.returnStart){out.phase='contact';out.progress=1;out.throwArm=mix(1.04,.78,smooth((t-CAST.contact)/.14));out.throwElbow=.09;out.spineLean=.075;}
  else if(t<CAST.end){const k=smooth((t-CAST.returnStart)/(CAST.end-CAST.returnStart));out.phase='return';out.progress=1-k;out.throwArm=mix(.78,0,k);out.throwElbow=mix(.09,0,k);out.spineLean=mix(.075,0,k);}
  return out;
 }
 function flight(t,from,to){
  const s=state(t),p=s.progress;
  const x=mix(from.x,to.x,p),z=mix(from.z,to.z,p);
  const travel=Math.hypot(to.x-from.x,to.z-from.z);
  const y=.42+(1.6+Math.min(1.6,travel*.14))*Math.sin(Math.PI*p);
  return {x,y,z,progress:p,phase:s.phase};
 }
 const api={CAST,state,flight};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 root.RaftCastMotion=api;
})(typeof window==='undefined'?globalThis:window);
