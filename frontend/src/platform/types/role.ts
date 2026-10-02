import type { Schema } from './api'

export type RoleIn = Schema<'RoleIn'>
export type RolePatch = Schema<'RolePatch'>
export type RolePermissionIn = Schema<'RolePermissionIn'>
export type RoleOut = Schema<'RoleOut'>
export type RoleBase = Pick<RoleOut, 'name' | 'description'>
