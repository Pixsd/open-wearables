<script lang="ts">
	import Plug from '@lucide/svelte/icons/plug';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Card from '$lib/components/ui/Card.svelte';
	import ConfirmDialog from '$lib/components/ui/ConfirmDialog.svelte';
	import CopyableId from '$lib/components/ui/CopyableId.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import IconButton from '$lib/components/ui/IconButton.svelte';
	import { formatRelativeTime } from '$lib/utils/datetime';
	import CredentialRow from './CredentialRow.svelte';
	import type { McpClient } from '$lib/settings/types';

	let {
		clients,
		messageFor
	}: {
		clients: McpClient[];
		messageFor: (action: string) => string | undefined;
	} = $props();

	let subject = $state<McpClient | null>(null);
	let forgetOpen = $state(false);

	const label = (client: McpClient) => client.client_name || 'Unnamed client';
</script>

<Card
	icon={Plug}
	title="Connected MCP clients"
	description="Apps that signed in to your MCP server through OAuth, such as claude.ai. Connections made with a bearer token have no identity of their own and are not listed."
>
	{#if clients.length === 0}
		<EmptyState
			icon={Plug}
			title="No MCP clients yet"
			description="A client appears here after it signs in through your MCP server."
		/>
	{:else}
		<div class="divide-y divide-border">
			{#each clients as client (client.id)}
				<CredentialRow icon={Plug} name={label(client)} created={client.created_at}>
					{#snippet identifier()}
						<CopyableId value={client.client_id} label="Client ID" visible={24} />
						<span>active {formatRelativeTime(client.last_seen_at)}</span>
					{/snippet}

					{#snippet actions()}
						<IconButton
							icon={Trash2}
							label="Forget {label(client)}"
							danger
							onclick={() => {
								subject = client;
								forgetOpen = true;
							}}
						/>
					{/snippet}
				</CredentialRow>
			{/each}
		</div>
	{/if}
</Card>

<ConfirmDialog
	bind:open={forgetOpen}
	title="Forget MCP client?"
	action="?/forgetMcpClient"
	confirmLabel="Forget"
	busyLabel="Forgetting…"
	destructive
	fields={{ id: subject?.id ?? '' }}
	message={messageFor('forgetMcpClient')}
>
	{subject ? label(subject) : 'This client'} leaves this list only. Its session on the MCP server stays
	valid, and it shows up again the next time it signs in.
</ConfirmDialog>
