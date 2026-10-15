// Browsing shortcuts only; original professional categories and legal scope stay intact.
export const BROWSE_GROUPS = [
  {id:'fire',label:'消防与疏散',categories:['消防安全']},
  {id:'equipment',label:'设备与用电',categories:['电气安全','机械设备与设施','特种设备']},
  {id:'chemicals',label:'危化品与防爆',categories:['危化品与燃气','粉尘防爆']},
  {id:'work',label:'作业与防护',categories:['作业安全','职业卫生']},
  {id:'place',label:'场所与环境',categories:['场所与标志','危险废物与环境']},
  {id:'management',label:'管理与应急',categories:['安全管理与培训','应急与事故管理']},
];

export function browseGroupMatches(row,id){
  if(!id)return true;
  const group=BROWSE_GROUPS.find(group=>group.id===id);
  return !!group?.categories.includes(row.displayCategory??row.category??'');
}
