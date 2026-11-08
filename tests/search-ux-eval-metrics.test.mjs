import test from 'node:test';
import assert from 'node:assert/strict';
import {matchExpectedIssues} from '../tools/checks/search_issue_metrics.mjs';

test('two expected hazards in one list cannot masquerade as correct multi-issue retrieval',()=>{
  const assignment=matchExpectedIssues([['H_A'],['H_B']],[['H_A','H_B'],[]]);
  assert.equal(assignment.filter(index=>index>=0).length,1);
});

test('independent groups can match distinct issue lists in either display order',()=>{
  assert.deepEqual(matchExpectedIssues([['H_A'],['H_B']],[['H_B'],['H_A']]),[1,0]);
});

test('overlapping acceptable labels still require an assignment covering both issues',()=>{
  assert.deepEqual(matchExpectedIssues([['H_A','H_B'],['H_A']],[['H_A'],['H_B']]),[1,0]);
  assert.deepEqual(matchExpectedIssues([],[]),[]);
});
