// A single retrieved issue must not receive credit for two independent expected
// hazards. Matching groups to distinct issue lists keeps multi-issue recall real.
export function matchExpectedIssues(expectedGroups, issueTopIds) {
  let best=expectedGroups.map(()=>-1),bestCount=-1;
  const visit=(group,used,assignment,count)=>{
    if(group===expectedGroups.length){
      if(count>bestCount){best=[...assignment];bestCount=count;}
      return;
    }
    for(let issue=0;issue<issueTopIds.length;issue++){
      if(used.has(issue)||!expectedGroups[group].some(id=>issueTopIds[issue].includes(id)))continue;
      used.add(issue);assignment.push(issue);visit(group+1,used,assignment,count+1);assignment.pop();used.delete(issue);
    }
    assignment.push(-1);visit(group+1,used,assignment,count);assignment.pop();
  };
  visit(0,new Set(),[],0);
  return best;
}
